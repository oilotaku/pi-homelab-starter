// 全域共用的 token 狀態(容器啟停/重啟、音量調整用),存 localStorage。
// 用單一 composable 讓 sidebar 的解鎖按鈕跟各個控制面板共享同一份狀態。
import { ref } from "vue";
import { getToken, setToken as persistToken } from "./api.js";

const token = ref(getToken());

export function useToken() {
  function unlock(value) {
    token.value = value.trim();
    persistToken(token.value);
  }
  function lock() {
    token.value = "";
    persistToken("");
  }
  return { token, unlock, lock };
}
