import { createClient } from "npm:@supabase/supabase-js@2";

const headers = {
  "Content-Type": "application/json",
  "Cache-Control": "no-store",
};
function result(status: number, error: string) {
  return new Response(JSON.stringify({ error }), { status, headers });
}
Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return result(405, "method_not_allowed");
  const bearer = req.headers.get("Authorization") || "";
  if (!bearer.startsWith("Bearer ")) return result(401, "not_authenticated");
  const token = bearer.slice(7);
  const url = Deno.env.get("SUPABASE_URL");
  const anon = Deno.env.get("SUPABASE_ANON_KEY");
  const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !anon || !service) return result(500, "server_not_configured");
  const userClient = createClient(url, anon, {
    global: { headers: { Authorization: bearer } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser(token);
  const user = userData.user;
  if (userError || !user || !user.email) return result(401, "invalid_session");
  let body: { password?: unknown };
  try { body = await req.json(); } catch { return result(400, "invalid_request"); }
  const password = body.password;
  if (typeof password !== "string" || !password || password.length > 256)
    return result(400, "password_required");
  // Re-authenticate using the email from the verified JWT, not a user-supplied identity.
  const checkClient = createClient(url, anon, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: checked, error: checkError } = await checkClient.auth.signInWithPassword({
    email: user.email, password,
  });
  if (checkError || checked.user?.id !== user.id) return result(403, "password_incorrect");

  const admin = createClient(url, service, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  // First delete files using the Storage API, never SQL DELETE on storage.objects.
  // Recursively list the user's private prefix, so unreferenced uploads are included.
  async function collect(prefix: string, depth = 0): Promise<string[]> {
    if (depth > 12) throw new Error("storage_depth_limit");
    const found: string[] = [];
    for (let offset = 0; ; offset += 100) {
      const { data, error } = await admin.storage.from("note-images")
        .list(prefix, { limit: 100, offset });
      if (error) throw new Error("storage_list_failed");
      if (!data?.length) break;
      for (const item of data) {
        const path = `${prefix}/${item.name}`;
        if (item.id) found.push(path);
        else found.push(...await collect(path, depth + 1));
      }
      if (data.length < 100) break;
    }
    return found;
  }
  try {
    const files = await collect(user.id);
    for (let i = 0; i < files.length; i += 100) {
      const { error } = await admin.storage.from("note-images").remove(files.slice(i, i + 100));
      if (error) return result(500, "storage_cleanup_failed");
    }
    // Notes and assets reference auth.users ON DELETE CASCADE (see sql/schema.sql).
    // Auth user deletion is LAST so failures in Storage cleanup don't remove the account.
    const { error: deleteError } = await admin.auth.admin.deleteUser(user.id);
    if (deleteError) return result(500, "auth_delete_failed");
    return new Response(JSON.stringify({ deleted: true }), { status: 200, headers });
  } catch (err) {
    console.error("delete-account failed", err instanceof Error ? err.message : "unknown");
    return result(500, "account_delete_failed");
  }
});
