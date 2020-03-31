API_URL = "https://api-public.sandbox.pro.coinbase.com";

function getCurrencies() {
  response = axios.get(`${API_URL}/${products}`);
  console.log(response);
}
