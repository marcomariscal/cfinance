$(function () {
  const $portfolioTableRow = $(".portfolio-table-row");
  const $currencyInfo = $(".currency-info");
  const $portfolioPieChart = $("#portfolio-pie-chart");
  const $portfolioPctTotal = $("#portfolio-pct-total");
  const $portfolioPctInputs = $(".portfolio-pct-input");
  const $arrows = $(".fas.fa-caret-up, .fas.fa-caret-down");
  const $rebalanceSubmit = $("#rebalance-submit");
  const $rebalanceForm = $("#rebalance-form");

  /** dashboard */
  // get pct of portfolio for each currency for pie chart
  async function portfolioAllocationPcts() {
    const { data } = await axios.get(`/api/users/portfolio_pcts`);
    const filteredData = _.pickBy(data, (x) => x !== 0);
    return filteredData;
  }

  // append pie chart to dom
  (async () => {
    let data = await portfolioAllocationPcts();
    const labels = Object.keys(data);
    const datasets = [
      {
        label: "% of Total Assets",
        data: Object.values(data),
        backgroundColor: [
          "rgba(255, 99, 132, 0.8)",
          "rgba(54, 162, 235, 0.8)",
          "rgba(255, 206, 86, 0.8)",
          "rgba(75, 192, 192, 0.8)",
          "rgba(153, 102, 255, 0.8)",
          "rgba(45, 102, 255, 0.8)",
        ],
        borderColor: [
          "rgba(255, 99, 132, 0.8)",
          "rgba(54, 162, 235, 0.8)",
          "rgba(255, 206, 86, 0.8)",
          "rgba(75, 192, 192, 0.8)",
          "rgba(153, 102, 255, 0.8)",
          "rgba(45, 102, 255, 0.8)",
        ],
        borderWidth: 0,
      },
    ];

    const options = {
      legend: false,
      tooltips: {
        xPadding: 50,
        yPadding: 10,
        mode: "nearest",
        backgroundColor: "rgba(114, 124, 255, 0.85)",
        bodyAlign: "center",
        titleFontSize: 18,
        titleFontColor: "#fff",
        titleAlign: "center",
        bodyFontFamily: "Karla",
        bodyFontColor: "#fff",
        bodyFontSize: 18,
        displayColors: false,
        cutoutPercentage: 60,
        callbacks: {
          title: (item, data) => data["labels"][item[0]["index"]],
          label: (item, data) =>
            `${data["datasets"][0]["data"][item["index"]].toFixed(2) * 100}%`,
        },
      },
    };

    const pieData = {
      labels: labels,
      datasets: datasets,
    };

    let ctx = $portfolioPieChart;
    let myPieChart = new Chart(ctx, {
      type: "doughnut",
      data: pieData,
      options: options,
    });
  })();

  /** rebalance route */

  function handlePctInputChange() {
    let portfolioPctSum = 0;
    $portfolioPctInputs.each((index, element) => {
      portfolioPctSum += parseInt(element.value);
    });

    // ensure all inputs exists
    isNaN(portfolioPctSum)
      ? $portfolioPctTotal.html("<p class='invalid-sum'>Updating...<p>")
      : $portfolioPctTotal.html(
          $(`<p>Target Allocation Total: ${portfolioPctSum}%</p>`)
        );

    // adjust class to highlight in red if inputs don't add up to 100%
    portfolioPctSum !== 100
      ? $portfolioPctTotal.children().addClass("invalid-sum")
      : $portfolioPctTotal.children().removeClass("invalid-sum");

    // disable rebalance button if inputs don't add up to 100%
    portfolioPctSum !== 100
      ? $rebalanceSubmit.prop("disabled", true)
      : $rebalanceSubmit.prop("disabled", false);
  }

  function handleArrowClick() {
    const $arrow = $(this);
    let $pctInput = $(this).parent().parent().siblings()[3].children[0];

    let pctInputVal = $pctInput.value;

    // check the class for up or down arrow to be able to increment or decrement accordingly
    $arrow.hasClass("fa-caret-up") ? pctInputVal++ : pctInputVal--;

    if (pctInputVal < 0 || pctInputVal > 100) return;
    $pctInput.value = pctInputVal;
  }

  // handle input changes in rebalance table
  $arrows.on("click", handleArrowClick);
  $portfolioPctInputs.on("input", handlePctInputChange);

  // show loading when rebalance is initiated
  $rebalanceSubmit.on("click", (e) => {
    $rebalanceForm.submit();
    e.preventDefault();
    $rebalanceSubmit.prop("disabled", true);
    // add spinner to rebalance button
    $rebalanceSubmit.html(
      '<span class="spinner-border mr-2" role="status" aria-hidden="true"></span>Rebalancing...'
    );
  });
});
