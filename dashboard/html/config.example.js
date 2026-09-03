// 複製這個檔案為 config.js 後依需求修改:
//   cp config.example.js config.js
// config.js 已被 .gitignore 排除,不會被推上 GitHub——機器相關的連線位址、
// 服務清單都寫在那份本機檔案裡,不用擔心之後不小心 commit 出去。
window.DASHBOARD_CONFIG = {
  // 找不到 window.location.hostname 時(例如直接用 file:// 打開)的備援連線位址
  fallbackHost: "",

  // 若你有自架 RSS 自動下載後端,填它的 port;沒有就留 null,首頁會自動隱藏那個表單
  rssApiPort: null,

  // 首頁的服務連結卡片,依分組顯示。下面只示範這個 repo 實際會幫你裝的 Pi-hole,
  // 把其他你自己機器上在跑的服務加進來即可。
  serviceGroups: [
    {
      title: "系統 / 網路",
      services: [
        { icon: "🛡️", name: "Pi-hole", desc: "DNS / 廣告過濾", port: 80, path: "/admin" },
      ],
    },
  ],
};
