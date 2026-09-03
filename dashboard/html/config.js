// 這個 dashboard 綁定特定機器的地方都集中在這裡——換一台機器用,
// 改這個檔案裡的值就好,不用動 index.html / index.js。
window.DASHBOARD_CONFIG = {
  // 找不到 window.location.hostname 時(例如直接用 file:// 打開)的備援連線位址
  fallbackHost: "192.168.17.148",

  // 「新增追番」RSS 自動下載表單背後打的後端 API port。
  // 這支後端(rss-manager)是另一支自架服務,不在這個 repo 裡——
  // 沒有這支後端就把這裡設成 null,首頁會自動隱藏這個表單。
  rssApiPort: 5090,

  // 首頁的服務連結卡片,依分組顯示。把這裡換成你自己機器上實際在跑的服務。
  serviceGroups: [
    {
      title: "媒體",
      services: [
        { icon: "🎬", name: "Jellyfin", desc: "影音串流", port: 8096, path: "" },
      ],
    },
    {
      title: "下載自動化",
      services: [
        { icon: "⬇️", name: "qBittorrent", desc: "BT 下載器", port: 8080, path: "" },
      ],
    },
    {
      title: "系統 / 網路",
      services: [
        { icon: "🛡️", name: "Pi-hole", desc: "DNS / 廣告過濾", port: 80, path: "/admin" },
      ],
    },
  ],
};
