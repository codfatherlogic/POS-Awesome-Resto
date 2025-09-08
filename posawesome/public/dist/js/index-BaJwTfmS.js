import { m as a, p as c } from "./posawesome.bundle-BxXNcK8v.js";
import { R as g, a as m, c as C, U as h, aH as d, n as S, aI as p, aE as O, a3 as I, am as y, ab as v, ag as P, z as k, aw as L, h as T, d as _, ac as x, ah as A, a6 as E, V as M, aA as B, W as D, aG as U, ay as F, aD as Q, at as G, av as b, j as H, l as J, r as R, ar as W, o as q, J as z, a1 as N, a4 as j, al as w, aa as K, af as X, A as V, x as Y, ad as Z, ai as $, E as ee, v as ae, g as se, f as te, K as ce, C as oe, G as ne, aJ as re, b as ie, i as le, Y as ue, X as fe, M as ge, a8 as me, Z as Ce, e as he, Q as de, P as Se, T as pe, S as Oe, aF as Ie, ax as ye, aC as ve, aq as Pe, s as ke, az as Le, as as Te, aj as _e, a9 as xe, ae as Ae, au as Ee, aK as Me, aB as Be, k as De, u as Ue, q as Fe, I as Qe, a5 as Ge, N as be, B as He, y as Je, F as Re, w as We, _ as qe, L as ze, D as Ne, H as je, ao as we, an as Ke, ap as Xe, t as Ve, O as Ye, a0 as Ze, a2 as $e, a7 as ea, ak as aa, $ as sa } from "./posawesome.bundle-BxXNcK8v.js";
function r(s, e) {
  try {
    const t = a.coupons_cache || {}, o = typeof structuredClone == "function" ? structuredClone(e) : JSON.parse(JSON.stringify(e));
    t[s] = o, a.coupons_cache = t, c("coupons_cache", a.coupons_cache);
  } catch (t) {
    console.error("Failed to cache coupons", t);
  }
}
function i(s) {
  try {
    return (a.coupons_cache || {})[s] || [];
  } catch (e) {
    return console.error("Failed to get cached coupons", e), [];
  }
}
function l(s) {
  try {
    const e = a.coupons_cache || {};
    if (s)
      delete e[s];
    else
      for (const t in e)
        delete e[t];
    a.coupons_cache = e, c("coupons_cache", a.coupons_cache);
  } catch (e) {
    console.error("Failed to clear coupons cache", e);
  }
}
export {
  g as MAX_QUEUE_ITEMS,
  m as addToPersistQueue,
  C as checkDbHealth,
  h as clearAllCache,
  l as clearCoupons,
  d as clearCustomerBalanceCache,
  S as clearCustomerStorage,
  p as clearExpiredCustomerBalances,
  O as clearItemGroups,
  I as clearLocalStockCache,
  y as clearOfflineCustomers,
  v as clearOfflineInvoices,
  P as clearOfflinePayments,
  k as clearOpeningStorage,
  L as clearPriceListCache,
  T as clearStoredItems,
  _ as db,
  x as deleteOfflineInvoice,
  A as deleteOfflinePayment,
  E as fetchItemStockQuantities,
  M as forceClearAllCache,
  B as getAllStoredItems,
  D as getCacheUsageEstimate,
  i as getCachedCoupons,
  U as getCachedCustomerBalance,
  F as getCachedItemDetails,
  Q as getCachedItemGroups,
  G as getCachedOffers,
  b as getCachedPriceListItems,
  H as getCustomerStorage,
  J as getCustomerStorageCount,
  R as getCustomersLastSync,
  W as getItemUOMs,
  q as getItemsLastSync,
  z as getLastSyncTotals,
  N as getLocalStock,
  j as getLocalStockCache,
  w as getOfflineCustomers,
  K as getOfflineInvoices,
  X as getOfflinePayments,
  V as getOpeningDialogStorage,
  Y as getOpeningStorage,
  Z as getPendingOfflineInvoiceCount,
  $ as getPendingOfflinePaymentCount,
  ee as getPrintTemplate,
  ae as getSalesPersonsStorage,
  se as getStoredItems,
  te as getStoredItemsCount,
  ce as getTaxInclusiveSetting,
  oe as getTaxTemplate,
  ne as getTermsAndConditions,
  re as getTranslationsCache,
  ie as initPersistWorker,
  le as initPromise,
  ue as initializeStockCache,
  fe as isCacheReady,
  ge as isManualOffline,
  me as isOffline,
  Ce as isStockCacheReady,
  a as memory,
  he as memoryInitPromise,
  c as persist,
  de as purgeOldQueueEntries,
  Se as queueHealthCheck,
  pe as reduceCacheUsage,
  Oe as resetOfflineState,
  r as saveCoupons,
  Ie as saveCustomerBalance,
  ye as saveItemDetailsCache,
  ve as saveItemGroups,
  Pe as saveItemUOMs,
  ke as saveItems,
  Le as saveItemsBulk,
  Te as saveOffers,
  _e as saveOfflineCustomer,
  xe as saveOfflineInvoice,
  Ae as saveOfflinePayment,
  Ee as savePriceListItems,
  Me as saveTranslationsCache,
  Be as searchStoredItems,
  De as setCustomerStorage,
  Ue as setCustomersLastSync,
  Fe as setItemsLastSync,
  Qe as setLastSyncTotals,
  Ge as setLocalStockCache,
  be as setManualOffline,
  He as setOpeningDialogStorage,
  Je as setOpeningStorage,
  Re as setPrintTemplate,
  We as setSalesPersonsStorage,
  qe as setStockCacheReady,
  ze as setTaxInclusiveSetting,
  Ne as setTaxTemplate,
  je as setTermsAndConditions,
  we as syncOfflineCustomers,
  Ke as syncOfflineInvoices,
  Xe as syncOfflinePayments,
  Ve as terminatePersistWorker,
  Ye as toggleManualOffline,
  Ze as updateLocalStock,
  $e as updateLocalStockCache,
  ea as updateLocalStockWithActualQuantities,
  aa as updateOfflineInvoicesCustomer,
  sa as validateStockForOfflineInvoice
};
