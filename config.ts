import "dotenv/config";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/, "phai la Discord ID hop le");

const schema = z.object({
  DISCORD_TOKEN: z.string().min(1, "thieu DISCORD_TOKEN"),
  DISCORD_CLIENT_ID: snowflake,
  DEV_GUILD_ID: snowflake.optional().or(z.literal("").transform(() => undefined)),

  DATABASE_URL: z.string().url(),

  // ID dev toan cuc — luon co toan quyen o MOI server, dung tren ca chu
  // server. De trong = khong co dev toan cuc.
  //
  // Cat o .env (da gitignore), KHONG bao gio trong source hay .env.example.
  // Bot cung khong bao gio in ID nay ra bat ky dau (xem features/admin).
  DEV_USER_ID: snowflake.optional().or(z.literal("").transform(() => undefined)),

  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  console.error("\n  Cau hinh .env khong hop le:\n");
  for (const issue of parsed.error.issues) {
    console.error(`    ${issue.path.join(".")}: ${issue.message}`);
  }
  console.error("\n  Copy .env.example thanh .env va dien vao.\n");
  process.exit(1);
}

const env = parsed.data;

export const config = {
  discord: {
    token: env.DISCORD_TOKEN,
    clientId: env.DISCORD_CLIENT_ID,
    devGuildId: env.DEV_GUILD_ID,
  },
  databaseUrl: env.DATABASE_URL,
  /// Dev toan cuc. undefined = tinh nang tat.
  devUserId: env.DEV_USER_ID,
  logLevel: env.LOG_LEVEL,
} as const;

// Cac nguong dieu chinh nam o limits.ts. De o day nua thi co hai nguon su
// that cho cung mot hang so — som muon cung lech nhau.

export type Config = typeof config;
