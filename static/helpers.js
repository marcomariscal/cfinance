API_URL = "https://api-public.sandbox.pro.coinbase.com";

function getCurrencyInfo(curr) {
  response = axios.get(`${API_URL}/${products}`);
  console.log(response);
}
