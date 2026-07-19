import {
  ButtonBuilder,
  ButtonStyle,
  ChannelType,
  Client,
  MessageFlags,
  ThreadAutoArchiveDuration,
  type TextChannel,
} from "discord.js";
import { MatchStatus } from "@prisma/client";
import { db } from "../db.js";
import { LIMITS } from "../limits.js";
import { ID } from "../lib/ids.js";
import { logger } from "../lib/logger.js";
import { sendDM } from "../lib/dm.js";
import { getProfile } from "./discovery.js";
import { matchRevealCard, notice } from "../ui/profileCard.js";
import { COLOR, GLYPH, sub } from "../ui/theme.js";
import { getGlyphConfig } from "./glyphConfig.js";

const log = logger("match");

/// Gui thong bao match qua DM kem nut opt-in.
///
/// KHONG tao thread o day. Match khong dong nghia voi "ca hai san sang chat
/// ngay bay gio". Bi keo vao mot thread luc 2h sang cung nguoi la la trai
/// nghiem toi. Thread chi ra doi khi CA HAI chu dong bam.
export async function announceMatch(client: Client, matchId: string): Promise<void> {
  const match = await db.match.findUnique({ where: { id: matchId } });
  if (!match || match.status !== MatchStatus.PENDING_OPT_IN) return;

  for (const [me, them] of [
    [match.userAId, match.userBId],
    [match.userBId, match.userAId],
  ] as const) {
    await dmOptIn(client, matchId, match.guildId, me, them).catch((e) =>
      log.debug(`khong DM duoc ${me}`, e?.message)
    );
  }
}

async function dmOptIn(
  client: Client,
  matchId: string,
  guildId: string,
  meId: string,
  themId: string
): Promise<void> {
  const them = await getProfile(guildId, themId);
  if (!them) return;

  // Loi nhan Super Like ho gui kem — neu co (super like la item boost rieng).
  const theirSuperLike = await db.superLikeSent.findUnique({
    where: { guildId_fromUserId_toUserId: { guildId, fromUserId: themId, toUserId: meId } },
  });

  const guild = await client.guilds.fetch(guildId).catch(() => null);

  const glyphs = await getGlyphConfig(guildId);
  const gp = (key: keyof typeof GLYPH) => glyphs.get(key) ?? GLYPH[key];

  const body = [
    `**${them.displayName}** cũng thích bạn.`,
    theirSuperLike?.note
      ? `\n> ${theirSuperLike.note}\n-# ${gp("superLike")} gửi kèm Super Like`
      : "",
  ]
    .filter(Boolean)
    .join("\n");

  const card = notice({
    color: COLOR.gold,
    title: `${gp("sparkle")} Match!`,
    body,
    footer:
      `Cả hai cùng bấm "Bắt đầu chat" thì bot mới mở phòng riêng. ` +
      `Không ai bị kéo vào đâu cả.\nLời mời hết hạn sau ${LIMITS.optInHours} giờ.` +
      (guild ? `  ${GLYPH.dot}  ${guild.name}` : ""),
    buttons: [
      new ButtonBuilder()
        .setCustomId(ID.matchReady(matchId))
        .setLabel("Bắt đầu chat")
        .setEmoji(gp("chat"))
        .setStyle(ButtonStyle.Success),
      new ButtonBuilder()
        .setCustomId(ID.matchDecline(matchId))
        .setLabel("Thôi, bỏ qua")
        .setStyle(ButtonStyle.Secondary),
    ],
  });

  const user = await client.users.fetch(meId);
  await sendDM(user, { components: [card], flags: MessageFlags.IsComponentsV2 });
}

export type ReadyOutcome =
  | { kind: "waiting" }
  | { kind: "opened"; threadId: string }
  | { kind: "gone" }
  | { kind: "expired" }
  | { kind: "full" }; // Da dat toi da 5 phong chat dang hoat dong

/// Dem so match ACTIVE hien tai cua mot user.
export async function countActiveMatches(guildId: string, userId: string): Promise<number> {
  return db.match.count({
    where: {
      guildId,
      status: MatchStatus.ACTIVE,
      OR: [{ userAId: userId }, { userBId: userId }],
    },
  });
}

/// Danh dau mot ben da san sang. Mo thread khi ca hai cung san sang.
export async function markReady(
  client: Client,
  matchId: string,
  userId: string
): Promise<ReadyOutcome> {
  const match = await db.match.findUnique({ where: { id: matchId } });
  if (!match) return { kind: "gone" };
  if (match.status === MatchStatus.ACTIVE && match.threadId) {
    return { kind: "opened", threadId: match.threadId };
  }
  if (match.status !== MatchStatus.PENDING_OPT_IN) return { kind: "gone" };
  if (match.optInExpiresAt < new Date()) return { kind: "expired" };

  const isA = match.userAId === userId;
  if (!isA && match.userBId !== userId) return { kind: "gone" };

  // Kiem tra so phong dang hoat dong cua user nay. Gioi han 5 la co y:
  // tranh tinh trang "chon nuoi" — lay match roi bo do, khong noi chuyen.
  const MAX_ACTIVE = 5;
  const activeCount = await countActiveMatches(match.guildId, userId);
  if (activeCount >= MAX_ACTIVE) return { kind: "full" };

  // updateMany + dieu kien status trong WHERE = compare-and-swap. Neu ben
  // kia vua doi status (decline/expire), update nay khong an gi ca.
  await db.match.updateMany({
    where: { id: matchId, status: MatchStatus.PENDING_OPT_IN },
    data: isA ? { userAReady: true } : { userBReady: true },
  });

  const fresh = await db.match.findUnique({ where: { id: matchId } });
  if (!fresh || fresh.status !== MatchStatus.PENDING_OPT_IN) return { kind: "gone" };
  if (!(fresh.userAReady && fresh.userBReady)) return { kind: "waiting" };

  const threadId = await openThread(client, matchId);
  return threadId ? { kind: "opened", threadId } : { kind: "gone" };
}

/// Tao private thread. Chi goi khi ca hai da san sang.
async function openThread(client: Client, matchId: string): Promise<string | null> {
  // Khoa bang chinh dieu kien update: chi ban nao chuyen duoc PENDING -> ACTIVE
  // moi duoc tao thread. Ngan 2 request song song tao ra 2 thread.
  const claimed = await db.match.updateMany({
    where: { id: matchId, status: MatchStatus.PENDING_OPT_IN, threadId: null },
    data: { status: MatchStatus.ACTIVE, lastActivityAt: new Date() },
  });
  if (claimed.count === 0) {
    const existing = await db.match.findUnique({ where: { id: matchId } });
    return existing?.threadId ?? null;
  }

  const match = await db.match.findUnique({ where: { id: matchId } });
  if (!match) return null;

  const cfg = await db.guildConfig.findUnique({ where: { guildId: match.guildId } });
  if (!cfg?.loungeChannelId) {
    log.error(`guild ${match.guildId} chua co loungeChannelId`);
    await db.match.update({
      where: { id: matchId },
      data: { status: MatchStatus.PENDING_OPT_IN },
    });
    return null;
  }

  const [a, b] = await Promise.all([
    getProfile(match.guildId, match.userAId),
    getProfile(match.guildId, match.userBId),
  ]);
  if (!a || !b) return null;

  try {
    const channel = (await client.channels.fetch(cfg.loungeChannelId)) as TextChannel;
    const thread = await channel.threads.create({
      name: `${a.displayName} & ${b.displayName}`,
      type: ChannelType.PrivateThread,
      // Khong cho thanh vien tu them nguoi khac vao. Day la phong rieng
      // cua hai nguoi, khong phai hangout.
      invitable: false,
      autoArchiveDuration: ThreadAutoArchiveDuration.ThreeDays,
      reason: `match ${matchId}`,
    });

    await db.match.update({ where: { id: matchId }, data: { threadId: thread.id } });

    await thread.members.add(match.userAId);
    await thread.members.add(match.userBId);

    const glyphs = await getGlyphConfig(match.guildId);

    // Moi nguoi thay card cua nguoi KIA (kem link MXH — day la luc socials
    // duoc tiet lo, phan thuong cho viec match).
    await thread.send({
      content: `<@${match.userAId}> <@${match.userBId}>`,
      components: [matchRevealCard(b, matchId, glyphs)],
      flags: MessageFlags.IsComponentsV2,
      allowedMentions: { users: [match.userAId, match.userBId] },
    });
    await thread.send({
      components: [matchRevealCard(a, matchId, glyphs)],
      flags: MessageFlags.IsComponentsV2,
    });
    await thread.send({
      content: sub(
        `Phòng này chỉ có hai bạn. Im lặng quá ${LIMITS.idleThreadHours} giờ thì bot sẽ tự dọn.`
      ),
    });

    const quizIntro = notice({
      color: COLOR.violet,
      title: "🎮 Minigame: Trắc nghiệm Ăn ý",
      body: "Để xua tan không khí ngại ngùng lúc đầu, hai bạn hãy thử chơi trò chơi trắc nghiệm 5 câu hỏi xem ăn ý tới mức nào nhé!",
      buttons: [
        new ButtonBuilder()
          .setCustomId(ID.quizStart(matchId))
          .setLabel("Chơi Quiz 🎮")
          .setStyle(ButtonStyle.Primary)
      ]
    });
    await thread.send({
      components: [quizIntro],
      flags: MessageFlags.IsComponentsV2,
    });

    return thread.id;
  } catch (err) {
    log.error(`tao thread that bai cho match ${matchId}`, err);
    await db.match.update({
      where: { id: matchId },
      data: { status: MatchStatus.PENDING_OPT_IN },
    });
    return null;
  }
}

export async function declineMatch(matchId: string, userId: string): Promise<boolean> {
  const res = await db.match.updateMany({
    where: {
      id: matchId,
      status: MatchStatus.PENDING_OPT_IN,
      OR: [{ userAId: userId }, { userBId: userId }],
    },
    data: { status: MatchStatus.EXPIRED, unmatchedBy: userId },
  });
  return res.count > 0;
}

/// Huy match. Cham dut vinh vien: hai nguoi khong bao gio thay lai nhau
/// (Swipe da ton tai nen discovery loai ho ra).
export async function unmatch(
  client: Client,
  matchId: string,
  byUserId: string
): Promise<boolean> {
  const match = await db.match.findUnique({ where: { id: matchId } });
  if (!match) return false;
  if (match.userAId !== byUserId && match.userBId !== byUserId) return false;
  if (match.status === MatchStatus.UNMATCHED) return false;

  await db.match.update({
    where: { id: matchId },
    data: { status: MatchStatus.UNMATCHED, unmatchedBy: byUserId },
  });

  const otherId = match.userAId === byUserId ? match.userBId : match.userAId;

  if (match.threadId) {
    try {
      const thread = await client.channels.fetch(match.threadId);
      if (thread?.isThread()) {
        await thread.send({
          components: [
            notice({
              color: COLOR.slate,
              title: "Match đã kết thúc",
              footer: "Phòng này sẽ được khoá.",
            }),
          ],
          flags: MessageFlags.IsComponentsV2,
        });
        await thread.setLocked(true, `unmatch boi ${byUserId}`);
        await thread.setArchived(true);
      }
    } catch (err) {
      log.debug(`khong dong duoc thread ${match.threadId}`, err);
    }
  }

  // Bao cho nguoi kia — trung tinh, khong quy loi, khong noi ai la nguoi huy.
  await client.users
    .fetch(otherId)
    .then((u) =>
      sendDM(u, {
        components: [
          notice({
            color: COLOR.slate,
            title: "Một match đã kết thúc",
            body: "Không sao cả — chuyện này bình thường.",
            footer: "Dùng /explore để tiếp tục.",
          }),
        ],
        flags: MessageFlags.IsComponentsV2,
      })
    )
    .catch(() => { });

  return true;
}

/// Nhung match dang cho user nay phan hoi. Day la duong lui khi user tat DM
/// — ho van thay va bam duoc tu /matches.
export async function pendingFor(guildId: string, userId: string) {
  return db.match.findMany({
    where: {
      guildId,
      status: MatchStatus.PENDING_OPT_IN,
      optInExpiresAt: { gt: new Date() },
      OR: [
        { userAId: userId },
        { userBId: userId },
      ],
    },
    orderBy: { createdAt: "desc" },
    take: 10,
  });
}

export async function activeFor(guildId: string, userId: string) {
  return db.match.findMany({
    where: {
      guildId,
      status: MatchStatus.ACTIVE,
      OR: [{ userAId: userId }, { userBId: userId }],
    },
    orderBy: { lastActivityAt: "desc" },
    take: 5,
  });
}

export function partnerOf(m: { userAId: string; userBId: string }, meId: string): string {
  return m.userAId === meId ? m.userBId : m.userAId;
}

