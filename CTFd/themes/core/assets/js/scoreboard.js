import Alpine from "alpinejs";
import CTFd from "./index";
import { getOption } from "./utils/graphs/echarts/scoreboard";
import { embed } from "./utils/graphs/echarts";

window.Alpine = Alpine;
window.CTFd = CTFd;

// Default scoreboard polling interval to every 5 minutes
const scoreboardUpdateInterval = window.scoreboardUpdateInterval || 300000;

// Helper: append competition_id query param when a competition page is active
function _appendCompetitionParam(url) {
  const cid = window.__CTF_COMPETITION_ID__;
  if (!cid) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}competition_id=${cid}`;
}

async function _getScoreboard(bracketId = null) {
  let url = "/api/v1/scoreboard";
  const params = [];
  if (bracketId) params.push(`bracket_id=${bracketId}`);
  if (window.__CTF_COMPETITION_ID__) params.push(`competition_id=${window.__CTF_COMPETITION_ID__}`);
  if (params.length) url += "?" + params.join("&");
  return (await (await CTFd.fetch(url, { method: "GET" })).json()).data;
}

async function _getScoreboardDetail(count, bracketId = null) {
  let url = `/api/v1/scoreboard/top/${count}`;
  const params = [];
  if (bracketId) params.push(`bracket_id=${bracketId}`);
  if (window.__CTF_COMPETITION_ID__) params.push(`competition_id=${window.__CTF_COMPETITION_ID__}`);
  if (params.length) url += "?" + params.join("&");
  return (await (await CTFd.fetch(url, { method: "GET" })).json()).data;
}

Alpine.data("ScoreboardDetail", () => ({
  data: {},
  show: true,
  activeBracket: null,

  async update() {
    this.data = await _getScoreboardDetail(10, this.activeBracket);

    let optionMerge = window.scoreboardChartOptions;
    let option = getOption(CTFd.config.userMode, this.data, optionMerge);

    embed(this.$refs.scoregraph, option);
    this.show = Object.keys(this.data).length > 0;
  },

  async init() {
    this.update();

    setInterval(() => {
      this.update();
    }, scoreboardUpdateInterval);
  },
}));

Alpine.data("ScoreboardList", () => ({
  standings: [],
  brackets: [],
  activeBracket: null,

  async update() {
    this.brackets = await CTFd.pages.scoreboard.getBrackets(CTFd.config.userMode);
    this.standings = await _getScoreboard(this.activeBracket);
  },

  async init() {
    this.$watch("activeBracket", value => {
      this.$dispatch("bracket-change", value);
    });

    this.update();

    setInterval(() => {
      this.update();
    }, scoreboardUpdateInterval);
  },
}));

Alpine.start();
