$(function () {
  const $portfolioTableRow = $(".portfolio-table-row");
  const $currencyInfo = $(".currency-info");
  const $portfolioPieChart = $("#portfolio-pie-chart");
  const $portfolioPctTotal = $("#portfolio-pct-total");
  const $portfolioPctInputs = $(".portfolio-pct-input");
  const $arrows = $(".fas.fa-caret-up, .fas.fa-caret-down");
  const $rebalanceSubmit = $("#rebalance-submit");

  $portfolioTableRow.on("click", function () {
    const id = $(this).attr("id");
    window.location = `/currencies/${id}`;
  });

  // get pct of portfolio for each currency for pie chart
  async function portfolioAllocationPcts() {
    const response = await axios.get(`/api/users/1/portfolio_pcts`);
    const data = response.data;
    return data;
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
        borderWidth: 1,
      },
    ];

    const options = {
      legend: false,
      tooltips: {
        backgroundColor: "rgba(0,0,0,1.0)",
        bodyFontColor: "rgba(255,255,255,1.0)",
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

  function handlePctInputChange() {
    let portfolioPctSum = 0;
    $portfolioPctInputs.each((index, element) => {
      portfolioPctSum += parseInt(element.value);
    });

    // adjust class to highlight in red if inputs don't add up to 100%
    portfolioPctSum !== 100
      ? $portfolioPctTotal.addClass("invalid-sum alert alert-warning")
      : $portfolioPctTotal.removeClass("invalid-sum alert alert-warning");

    // disable rebalance button if inputs don't add up to 100%
    portfolioPctSum !== 100
      ? $rebalanceSubmit.prop("disabled", true)
      : $rebalanceSubmit.prop("disabled", false);

    // ensure all inputs exists
    isNaN(portfolioPctSum)
      ? $portfolioPctTotal.html("Updating...")
      : $portfolioPctTotal.html(
          $(`<p>Current Allocation Total: ${portfolioPctSum}%</p>`)
        );
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

  $arrows.on("click", handleArrowClick);
  $portfolioPctInputs.on("input", handlePctInputChange);
});
