import { CupidPermission } from "@prisma/client";

/// Metadata quyen — du lieu thuan, khong dung db. permissions.ts (co db)
/// re-export lai de noi khac import tu mot cho.

export const ALL_PERMISSIONS = Object.values(CupidPermission);

export const PERMISSION_LABEL: Record<CupidPermission, string> = {
  GIVE_SUPERLIKE: "Cấp Super Like",
  REVIEW_REPORTS: "Xử lý báo cáo",
  MODERATE_PROFILE: "Cấm / bỏ cấm hồ sơ",
  VIEW_STATS: "Xem số liệu",
};

export const PERMISSION_HINT: Record<CupidPermission, string> = {
  GIVE_SUPERLIKE: "Cấp và thu hồi Super Like cho thành viên",
  REVIEW_REPORTS: "Đọc báo cáo, đánh dấu đã xử lý hoặc bỏ qua",
  MODERATE_PROFILE: "Cấm hồ sơ vi phạm, bỏ cấm, bỏ ẩn",
  VIEW_STATS: "Xem thống kê server",
};

/// Anh xa: subcommand cua /cupid  ->  quyen no doi hoi.
///
/// Day la du lieu thuan (khong dung db) de selftest kiem chung duoc ma khong
/// can token. Va no la NGUON SU THAT DUY NHAT: handleCupid tra cuu bang nay,
/// selftest doi chieu no voi danh sach subcommand that.
///
/// Vi sao quan trong: neu them mot subcommand /cupid ma quen them vao day,
/// handleCupid se khong tim thay quyen va tra ve som — lenh "khong lam gi",
/// im lang khong loi. Selftest bat duoc dieu do truoc khi deploy.
export const CUPID_REQUIRED: Record<string, CupidPermission> = {
  give: CupidPermission.GIVE_SUPERLIKE,
  balance: CupidPermission.GIVE_SUPERLIKE,
  reports: CupidPermission.REVIEW_REPORTS,
  resolve: CupidPermission.REVIEW_REPORTS,
  ban: CupidPermission.MODERATE_PROFILE,
  unban: CupidPermission.MODERATE_PROFILE,
  status: CupidPermission.VIEW_STATS,
};
