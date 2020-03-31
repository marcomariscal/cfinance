$(function() {
  const $portfolioTableRow = $(".portfolio-table-row");
  const $currencyInfo = $(".currency-info");

  $portfolioTableRow.on("click", function() {
    const id = $(this).attr("id");
    window.location = `/currencies/${id}`;
  });
});
