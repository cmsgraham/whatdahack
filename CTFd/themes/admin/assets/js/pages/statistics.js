import "./main";
import CTFd from "../compat/CTFd";
import $ from "jquery";
import echarts from "echarts/dist/echarts.common";
import { colorHash } from "../compat/styles";
import Vue from "vue";
import ScoreboardMatrix from "../components/statistics/ScoreboardMatrix.vue";

/* ──────────────────────────────────────────────────────────────────────
   whatdahack — futuristic ECharts theme (Akamai blue palette)
   ────────────────────────────────────────────────────────────────────── */
const AK = {
  vibrant: "#00A4EB",
  blue: "#36B5F0",
  deep: "#0061A8",
  cyan: "#00D1FF",
  orange: "#FF8B00",
};

const AK_PALETTE = [
  "#00A4EB",
  "#36B5F0",
  "#00D1FF",
  "#0061A8",
  "#7DD3FC",
  "#FF8B00",
  "#FFB454",
  "#5EEAD4",
  "#A78BFA",
  "#1E6FB8",
];

const isDark = () =>
  (document.documentElement.getAttribute("data-bs-theme") || "dark") !==
  "light";

function registerAkamaiTheme() {
  const dark = isDark();
  const text = dark ? "#c9d1d9" : "#41505f";
  const textStrong = dark ? "#e6edf3" : "#1f2933";
  const axisLine = dark ? "rgba(139,148,158,.30)" : "rgba(80,90,100,.30)";
  const split = dark ? "rgba(54,181,240,.10)" : "rgba(0,97,168,.12)";

  echarts.registerTheme("whatdahack", {
    color: AK_PALETTE,
    backgroundColor: "transparent",
    textStyle: { fontFamily: "Raleway, Lato, sans-serif", color: text },
    title: {
      left: "center",
      textStyle: {
        color: textStrong,
        fontFamily: "Raleway, Lato, sans-serif",
        fontWeight: 700,
        fontSize: 16,
      },
    },
    legend: { textStyle: { color: text } },
    tooltip: {
      backgroundColor: dark ? "rgba(22,27,34,.96)" : "rgba(255,255,255,.97)",
      borderColor: dark ? "rgba(54,181,240,.35)" : "rgba(0,97,168,.25)",
      borderWidth: 1,
      textStyle: { color: textStrong },
      extraCssText:
        "backdrop-filter:blur(10px);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.40);padding:10px 14px;",
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: axisLine } },
      axisTick: { lineStyle: { color: axisLine } },
      axisLabel: { color: text },
      splitLine: { show: false, lineStyle: { color: split } },
      nameTextStyle: { color: text },
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: text },
      splitLine: { lineStyle: { color: split, type: "dashed" } },
      nameTextStyle: { color: text },
    },
    toolbox: {
      iconStyle: { borderColor: text },
      emphasis: { iconStyle: { borderColor: AK.vibrant } },
    },
  });
}

/* Apply futuristic series styling (gradients, glow, rounded geometry). */
function futurize(option) {
  if (!option || !option.series) return option;

  const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
  const horizontalBar = xAxis && xAxis.type === "value";

  const barGradient = horizontalBar
    ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: AK.deep },
        { offset: 1, color: AK.cyan },
      ])
    : new echarts.graphic.LinearGradient(0, 1, 0, 0, [
        { offset: 0, color: AK.deep },
        { offset: 1, color: AK.cyan },
      ]);

  option.series.forEach((s) => {
    if (s.type === "bar") {
      s.itemStyle = {
        borderRadius: 6,
        color: barGradient,
        shadowColor: "rgba(0,164,235,.45)",
        shadowBlur: 14,
      };
      s.emphasis = {
        itemStyle: {
          shadowBlur: 26,
          shadowColor: "rgba(0,209,255,.70)",
          color: new echarts.graphic.LinearGradient(
            horizontalBar ? 0 : 0,
            horizontalBar ? 0 : 1,
            horizontalBar ? 1 : 0,
            0,
            [
              { offset: 0, color: AK.blue },
              { offset: 1, color: AK.vibrant },
            ],
          ),
        },
      };
      s.barWidth = s.barWidth || "55%";
    }

    if (s.type === "pie") {
      s.radius = ["44%", "70%"];
      s.itemStyle = Object.assign(
        {
          borderRadius: 8,
          borderColor: isDark() ? "#0d1117" : "#ffffff",
          borderWidth: 3,
          shadowColor: "rgba(0,0,0,.28)",
          shadowBlur: 12,
        },
        s.itemStyle,
      );
      s.label = Object.assign({}, s.label, {
        color: isDark() ? "#c9d1d9" : "#41505f",
      });
      s.labelLine = Object.assign({}, s.labelLine, {
        lineStyle: { color: isDark() ? "rgba(139,148,158,.5)" : "rgba(80,90,100,.5)" },
      });
      s.emphasis = Object.assign({}, s.emphasis, {
        scale: true,
        scaleSize: 10,
        itemStyle: { shadowBlur: 26, shadowColor: "rgba(0,164,235,.60)" },
      });
    }
  });

  if (option.dataZoom) {
    option.dataZoom.forEach((dz) => {
      if (dz.fillerColor) dz.fillerColor = "rgba(0,164,235,0.16)";
      dz.borderColor = "rgba(54,181,240,.25)";
      dz.handleStyle = { color: AK.blue, borderColor: AK.vibrant };
      dz.dataBackground = {
        lineStyle: { color: "rgba(54,181,240,.45)" },
        areaStyle: { color: "rgba(54,181,240,.12)" },
      };
      dz.selectedDataBackground = {
        lineStyle: { color: AK.vibrant },
        areaStyle: { color: "rgba(0,164,235,.22)" },
      };
    });
  }

  // The glass panel header already names each chart — hide the in-chart title
  // and the axis-name labels that were colliding with long category labels.
  if (option.title) option.title = { show: false };

  ["xAxis", "yAxis"].forEach((axisKey) => {
    if (!option[axisKey]) return;
    const axes = Array.isArray(option[axisKey])
      ? option[axisKey]
      : [option[axisKey]];
    axes.forEach((axis) => {
      axis.name = "";
      if (axis.type === "category") {
        axis.axisLabel = Object.assign({}, axis.axisLabel, {
          formatter: (val) =>
            typeof val === "string" && val.length > 16
              ? val.slice(0, 15) + "…"
              : val,
        });
      }
    });
  });

  // Reserve room so labels and zoom sliders never overlap or clip.
  const hasTopSlider =
    Array.isArray(option.dataZoom) &&
    option.dataZoom.some((dz) => dz.type === "slider" && dz.top !== undefined);
  option.grid = Object.assign(
    {
      left: "2%",
      right: "5%",
      top: hasTopSlider ? 58 : 24,
      bottom: "3%",
      containLabel: true,
    },
    option.grid,
  );

  return option;
}

const graph_configs = {
  "#solves-graph": {
    data: () => CTFd.api.get_challenge_solve_statistics(),
    format: (response) => {
      const data = response.data;
      const chals = [];
      const counts = [];
      const solves = {};
      for (let c = 0; c < data.length; c++) {
        solves[data[c]["id"]] = {
          name: data[c]["name"],
          solves: data[c]["solves"],
        };
      }

      const solves_order = Object.keys(solves).sort(function (a, b) {
        return solves[b].solves - solves[a].solves;
      });

      $.each(solves_order, function (key, value) {
        chals.push(solves[value].name);
        counts.push(solves[value].solves);
      });

      const option = {
        title: {
          left: "center",
          text: "Solve Counts",
        },
        tooltip: {
          trigger: "item",
        },
        toolbox: {
          show: true,
          feature: {
            mark: { show: true },
            dataView: { show: true, readOnly: false },
            magicType: { show: true, type: ["line", "bar"] },
            restore: { show: true },
            saveAsImage: { show: true },
          },
        },
        xAxis: {
          name: "Solve Count",
          nameLocation: "middle",
          type: "value",
        },
        yAxis: {
          name: "Challenge Name",
          nameLocation: "middle",
          nameGap: 60,
          type: "category",
          data: chals,
          axisLabel: {
            interval: 0,
            rotate: 0, //If the label names are too long you can manage this by rotating the label.
          },
        },
        dataZoom: [
          {
            show: false,
            start: 0,
            end: 100,
          },
          {
            type: "inside",
            yAxisIndex: 0,
            show: true,
            width: 20,
          },
          {
            fillerColor: "rgba(233, 236, 241, 0.4)",
            show: true,
            yAxisIndex: 0,
            width: 20,
          },
        ],
        series: [
          {
            itemStyle: { color: "#1f76b4" },
            data: counts,
            type: "bar",
          },
        ],
      };

      return option;
    },
  },

  "#keys-pie-graph": {
    data: () => CTFd.api.get_submission_property_counts({ column: "type" }),
    format: (response) => {
      const data = response.data;
      const solves = data["correct"];
      const fails = data["incorrect"];

      let option = {
        title: {
          left: "center",
          text: "Submission Percentages",
        },
        tooltip: {
          trigger: "item",
        },
        toolbox: {
          show: true,
          feature: {
            dataView: { show: true, readOnly: false },
            saveAsImage: {},
          },
        },
        legend: {
          orient: "vertical",
          top: "middle",
          right: 0,
          data: ["Fails", "Solves"],
        },
        series: [
          {
            name: "Submission Percentages",
            type: "pie",
            radius: ["30%", "50%"],
            avoidLabelOverlap: false,
            label: {
              show: true,
              formatter: function (data) {
                return `${data.name} (${data.value})\n${data.percent.toFixed(1)}%`;
              },
            },
            labelLine: {
              show: true,
            },
            emphasis: {
              label: {
                show: true,
                fontSize: "30",
                fontWeight: "bold",
              },
            },
            data: [
              {
                value: fails,
                name: "Fails",
                itemStyle: { color: "#FF5C5C" },
              },
              {
                value: solves,
                name: "Solves",
                itemStyle: { color: "#00A4EB" },
              },
            ],
          },
        ],
      };

      return option;
    },
  },

  "#categories-pie-graph": {
    data: () => CTFd.api.get_challenge_property_counts({ column: "category" }),
    format: (response) => {
      const data = response.data;

      const categories = [];
      const count = [];

      for (let category in data) {
        if (Object.hasOwn(data, category)) {
          categories.push(category);
          count.push(data[category]);
        }
      }

      for (let i = 0; i < data.length; i++) {
        categories.push(data[i].category);
        count.push(data[i].count);
      }

      let option = {
        title: {
          left: "center",
          text: "Category Breakdown",
        },
        tooltip: {
          trigger: "item",
        },
        toolbox: {
          show: true,
          feature: {
            dataView: { show: true, readOnly: false },
            saveAsImage: {},
          },
        },
        legend: {
          type: "plain",
          orient: "horizontal",
          top: "bottom",
          data: [],
        },
        series: [
          {
            name: "Category Breakdown",
            type: "pie",
            radius: ["30%", "50%"],
            label: {
              show: true,
              formatter: function (data) {
                return `${data.name} (${data.value})\n${data.percent.toFixed(1)}%`;
              },
            },
            labelLine: {
              show: true,
            },
            emphasis: {
              label: {
                show: true,
                fontSize: "30",
                fontWeight: "bold",
              },
            },
            data: [],
          },
        ],
      };

      categories.forEach((category, index) => {
        option.legend.data.push(category);
        option.series[0].data.push({
          value: count[index],
          name: category,
          itemStyle: { color: colorHash(category) },
        });
      });

      return option;
    },
  },

  "#points-pie-graph": {
    data: () => {
      return CTFd.fetch(
        "/api/v1/statistics/challenges/category?function=sum&target=value",
        {
          method: "GET",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
        },
      ).then(function (response) {
        return response.json();
      });
    },
    format: (response) => {
      const data = response.data;

      const categories = [];
      const count = [];

      for (let category in data) {
        if (Object.hasOwn(data, category)) {
          categories.push(category);
          count.push(data[category]);
        }
      }

      for (let i = 0; i < data.length; i++) {
        categories.push(data[i].category);
        count.push(data[i].count);
      }

      let option = {
        title: {
          left: "center",
          text: "Point Breakdown",
        },
        tooltip: {
          trigger: "item",
        },
        toolbox: {
          show: true,
          feature: {
            dataView: { show: true, readOnly: false },
            saveAsImage: {},
          },
        },
        legend: {
          type: "plain",
          orient: "horizontal",
          top: "bottom",
          data: [],
        },
        series: [
          {
            name: "Point Breakdown",
            type: "pie",
            radius: ["30%", "50%"],
            label: {
              show: true,
              formatter: function (data) {
                return `${data.name} (${data.value})\n${data.percent.toFixed(1)}%`;
              },
            },
            labelLine: {
              show: true,
            },
            emphasis: {
              label: {
                show: true,
                fontSize: "30",
                fontWeight: "bold",
              },
            },
            data: [],
          },
        ],
      };

      categories.forEach((category, index) => {
        option.legend.data.push(category);
        option.series[0].data.push({
          value: count[index],
          name: category,
          itemStyle: { color: colorHash(category) },
        });
      });

      return option;
    },
  },

  "#solve-percentages-graph": {
    layout: (annotations) => ({
      title: "Solve Percentages per Challenge",
      xaxis: {
        title: "Challenge Name",
      },
      yaxis: {
        title: `Percentage of ${
          CTFd.config.userMode.charAt(0).toUpperCase() +
          CTFd.config.userMode.slice(1)
        } (%)`,
        range: [0, 100],
      },
      annotations: annotations,
    }),
    data: () => CTFd.api.get_challenge_solve_percentages(),
    format: (response) => {
      const data = response.data;

      const names = [];
      const percents = [];

      const annotations = [];

      for (let key in data) {
        names.push(data[key].name);
        percents.push(data[key].percentage * 100);

        const result = {
          x: data[key].name,
          y: data[key].percentage * 100,
          text: Math.round(data[key].percentage * 100) + "%",
          xanchor: "center",
          yanchor: "bottom",
          showarrow: false,
        };
        annotations.push(result);
      }

      const option = {
        title: {
          left: "center",
          text: "Solve Percentages per Challenge",
        },
        tooltip: {
          trigger: "item",
          formatter: function (data) {
            return `${echarts.format.encodeHTML(data.name)} - ${(
              Math.round(data.value * 10) / 10
            ).toFixed(1)}%`;
          },
        },
        toolbox: {
          show: true,
          feature: {
            mark: { show: true },
            dataView: { show: true, readOnly: false },
            magicType: { show: true, type: ["line", "bar"] },
            restore: { show: true },
            saveAsImage: { show: true },
          },
        },
        xAxis: {
          name: "Challenge Name",
          nameGap: 40,
          nameLocation: "middle",
          type: "category",
          data: names,
          axisLabel: {
            interval: 0,
            rotate: 50,
          },
        },
        yAxis: {
          name: `"Percentage of ${
            CTFd.config.userMode.charAt(0).toUpperCase() +
            CTFd.config.userMode.slice(1)
          } (%)`,
          nameGap: 50,
          nameLocation: "middle",
          type: "value",
          min: 0,
          max: 100,
        },
        dataZoom: [
          {
            show: false,
            start: 0,
            end: 100,
          },
          {
            type: "inside",
            show: true,
            start: 0,
            end: 100,
          },
          {
            fillerColor: "rgba(233, 236, 241, 0.4)",
            show: true,
            right: 60,
            yAxisIndex: 0,
            width: 20,
          },
          {
            type: "slider",
            fillerColor: "rgba(233, 236, 241, 0.4)",
            top: 35,
            height: 20,
            show: true,
            start: 0,
            end: 100,
          },
        ],
        series: [
          {
            itemStyle: { color: "#1f76b4" },
            data: percents,
            type: "bar",
          },
        ],
      };

      return option;
    },
  },

  "#score-distribution-graph": {
    layout: (annotations) => ({
      title: "Score Distribution",
      xaxis: {
        title: "Score Bracket",
        showticklabels: true,
        type: "category",
      },
      yaxis: {
        title: `Number of ${
          CTFd.config.userMode.charAt(0).toUpperCase() +
          CTFd.config.userMode.slice(1)
        }`,
      },
      annotations: annotations,
    }),
    data: () =>
      CTFd.fetch("/api/v1/statistics/scores/distribution").then(
        function (response) {
          return response.json();
        },
      ),
    format: (response) => {
      const data = response.data.brackets;
      const keys = [];
      const brackets = [];
      const sizes = [];

      for (let key in data) {
        keys.push(parseInt(key));
      }
      keys.sort((a, b) => a - b);

      let start = "<0";
      keys.map((key) => {
        brackets.push(`${start} - ${key}`);
        sizes.push(data[key]);
        start = key;
      });

      const option = {
        title: {
          left: "center",
          text: "Score Distribution",
        },
        tooltip: {
          trigger: "item",
        },
        toolbox: {
          show: true,
          feature: {
            mark: { show: true },
            dataView: { show: true, readOnly: false },
            magicType: { show: true, type: ["line", "bar"] },
            restore: { show: true },
            saveAsImage: { show: true },
          },
        },
        xAxis: {
          name: "Score Bracket",
          nameGap: 40,
          nameLocation: "middle",
          type: "category",
          data: brackets,
        },
        yAxis: {
          name: `Number of ${
            CTFd.config.userMode.charAt(0).toUpperCase() +
            CTFd.config.userMode.slice(1)
          }`,
          nameGap: 50,
          nameLocation: "middle",
          type: "value",
        },
        dataZoom: [
          {
            show: false,
            start: 0,
            end: 100,
          },
          {
            type: "inside",
            show: true,
            start: 0,
            end: 100,
          },
          {
            fillerColor: "rgba(233, 236, 241, 0.4)",
            show: true,
            right: 60,
            yAxisIndex: 0,
            width: 20,
          },
          {
            type: "slider",
            fillerColor: "rgba(233, 236, 241, 0.4)",
            top: 35,
            height: 20,
            show: true,
            start: 0,
            end: 100,
          },
        ],
        series: [
          {
            itemStyle: { normal: { color: "#1f76b4" } },
            data: sizes,
            type: "bar",
          },
        ],
      };

      return option;
    },
  },
};

const createGraphs = () => {
  registerAkamaiTheme();
  for (let key in graph_configs) {
    const cfg = graph_configs[key];

    const $elem = $(key);
    $elem.empty();

    let chart = echarts.init(document.querySelector(key), "whatdahack", {
      renderer: "canvas",
    });

    cfg
      .data()
      .then(cfg.format)
      .then(futurize)
      .then((option) => {
        chart.setOption(option);
        $(window).on("resize", function () {
          if (chart != null && chart != undefined) {
            chart.resize();
          }
        });
      });
  }
};

function updateGraphs() {
  registerAkamaiTheme();
  for (let key in graph_configs) {
    const cfg = graph_configs[key];
    let chart = echarts.init(document.querySelector(key), "whatdahack", {
      renderer: "canvas",
    });
    cfg
      .data()
      .then(cfg.format)
      .then(futurize)
      .then((option) => {
        chart.setOption(option);
      });
  }
}

$(() => {
  createGraphs();
  setInterval(updateGraphs, 300000);

  const scoreboardMatrix = Vue.extend(ScoreboardMatrix);
  // Clear the spinner
  document.querySelector("#scoreboard-matrix").innerHTML = "";
  let scoreboardMatrixContainer = document.createElement("div");
  document
    .querySelector("#scoreboard-matrix")
    .appendChild(scoreboardMatrixContainer);

  new scoreboardMatrix().$mount(scoreboardMatrixContainer);
});
