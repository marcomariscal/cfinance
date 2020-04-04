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

    const labels = null;
    const datasets = [
      {
        label: "% of Total Assets",
        data: Object.values(data),
        backgroundColor: [
          "rgba(255, 99, 132, 0.2)",
          "rgba(54, 162, 235, 0.2)",
          "rgba(255, 206, 86, 0.2)",
          "rgba(75, 192, 192, 0.2)",
          "rgba(153, 102, 255, 0.2)"
        ],
        borderColor: [
          "rgba(255, 99, 132, 1)",
          "rgba(54, 162, 235, 1)",
          "rgba(255, 206, 86, 1)",
          "rgba(75, 192, 192, 1)",
          "rgba(153, 102, 255, 1)"
        ],
        borderWidth: 1
      }
    ];

    const options = {};

    const pieData = {
      labels: labels,
      datasets: datasets
    };

    let ctx = $portfolioPieChart;
    let myPieChart = new Chart(ctx, {
      type: "pie",
      data: pieData,
      options: options
    });
  })();
});
