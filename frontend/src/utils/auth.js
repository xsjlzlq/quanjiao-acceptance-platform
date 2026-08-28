/**
 * 权限判断工具函数
 * @param {string} permKey 权限标识 (如 'neiye_export_att6')
 * @returns {boolean}
 */
export function hasPerm(permKey) {
  const role = localStorage.getItem('auth_role');
  if (role === 'admin') return true;
  try {
    const perms = JSON.parse(localStorage.getItem('auth_perms') || '{}');
    // 如果没有配置该 key，默认为 true；显式为 false 时才拒绝
    return perms[permKey] !== false;
  } catch (e) {
    return true;
  }
}