$(function() {
  const $portfolioTableRow = $(".portfolio-table-row");
  const $currencyInfo = $(".currency-info");
  const $portfolioPieChart = $("#portfolio-pie-chart");

  $portfolioTableRow.on("click", function() {
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
          "rgba(45, 102, 255, 0.8)"
        ],
        borderColor: [
          "rgba(255, 99, 132, 0.8)",
          "rgba(54, 162, 235, 0.8)",
          "rgba(255, 206, 86, 0.8)",
          "rgba(75, 192, 192, 0.8)",
          "rgba(153, 102, 255, 0.8)",
          "rgba(45, 102, 255, 0.8)"
        ],
        borderWidth: 1
      }
    ];

    const options = {
      legend: false,
      tooltips: {
        backgroundColor: "rgba(0,0,0,1.0)",
        bodyFontColor: "rgba(255,255,255,1.0)"
      }
    };

    const pieData = {
      labels: labels,
      datasets: datasets
    };

    let ctx = $portfolioPieChart;
    let myPieChart = new Chart(ctx, {
      type: "doughnut",
      data: pieData,
      options: options
    });
  })();
});
