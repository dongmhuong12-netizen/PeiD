import { PrismaClient } from "@prisma/client";
import { config } from "./config.js";

export const db = new PrismaClient({
  datasources: { db: { url: config.databaseUrl } },
  log: config.logLevel === "debug" ? ["warn", "error", "query"] : ["warn", "error"],
});

// orderPair / isUniqueViolation da chuyen sang lib/pair.ts — chung la logic
// thuan va khong nen keo theo ket noi database khi import.
export { orderPair, isUniqueViolation, UNIQUE_VIOLATION } from "./lib/pair.js";
