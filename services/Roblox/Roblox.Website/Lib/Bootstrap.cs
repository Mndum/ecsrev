using Dapper;
using Roblox.Logging;
using Roblox.Models.Users;
using Roblox.Services;

namespace Roblox.Website.Lib;

/// <summary>
/// Creates the accounts a fresh install needs (the README's manual "ROBLOX", "UGC" and "BadDecisions" steps).
/// Only runs when Bootstrap:OwnerPassword is set in appsettings.json, and only for accounts that do not exist yet,
/// so it is safe to leave enabled.
/// </summary>
public static class Bootstrap
{
    private static async Task EnsureUser(UsersService us, long id, string username, string password)
    {
        var existing = await us.db.QuerySingleOrDefaultAsync("SELECT id FROM \"user\" WHERE id = :id", new { id });
        if (existing != null)
            return;
        try
        {
            await us.CreateUser(username, password, Gender.Unknown, id);
        }
        catch (Exception e)
        {
            // Avatar rendering happens after the account is committed and needs the (optional) render service.
            Console.WriteLine("[bootstrap] CreateUser({0}) threw: {1}", username, e.Message);
        }

        var created = await us.db.QuerySingleOrDefaultAsync("SELECT id FROM \"user\" WHERE id = :id", new { id });
        if (created == null)
            throw new Exception("Bootstrap could not create user " + username);
        Console.WriteLine("[bootstrap] created user {0} (id {1})", username, id);
    }

    public static async Task Run(string? ownerPassword)
    {
        if (string.IsNullOrWhiteSpace(ownerPassword))
            return;
        using var us = Roblox.Services.ServiceProvider.GetOrCreate<UsersService>();

        // ROBLOX = owner/admin account (id must match OwnerUserId, which is 1).
        await EnsureUser(us, 1, "ROBLOX", ownerPassword);
        // Owner is approved to use the site.
        await us.db.ExecuteAsync(
            "INSERT INTO user_invite (id, user_id, author_id) SELECT :id, 1, 1 WHERE NOT EXISTS (SELECT 1 FROM user_invite WHERE user_id = 1)",
            new { id = Guid.NewGuid().ToString() });

        // UGC: system account that owns user-made content. Gets a random password nobody knows, so nobody can log in.
        await EnsureUser(us, 2, "UGC", Guid.NewGuid().ToString("N") + "aA1!");

        // BadDecisions: receives items moved by GDPR deletions / inventory removals. Must be permanently banned.
        var firstTime = await us.db.QuerySingleOrDefaultAsync("SELECT id FROM \"user\" WHERE id = 12") == null;
        await EnsureUser(us, 12, "BadDecisions", Guid.NewGuid().ToString("N") + "aA1!");
        if (firstTime)
        {
            await us.db.ExecuteAsync(
                "INSERT INTO user_ban (user_id, reason, author_user_id, expired_at, internal_reason) VALUES (12, 'System account', 1, NULL, 'System account')");
            await us.db.ExecuteAsync("UPDATE \"user\" SET status = :st WHERE id = 12",
                new { st = AccountStatus.Deleted });

            // The accounts above were inserted with explicit ids, which does not advance the id sequence.
            // Without this the first real signup would try to take id 1 and fail.
            await us.db.ExecuteAsync(
                "SELECT setval(pg_get_serial_sequence('\"user\"', 'id'), GREATEST((SELECT MAX(id) FROM \"user\"), 12))");
        }
    }
}
