const URL = process.env.NODE_EXAMPLE_URL || "http://127.0.0.1:5200/orders";
const BODY = {item: "Buku Pemrograman", quantity: 1};


async function kirim(judul, headers) {
  const response = await fetch(URL, {
    method: "POST",
    headers: {
      "Authorization": "Bearer node-app-token",
      "Content-Type": "application/json",
      ...headers
    },
    body: JSON.stringify(BODY)
  });
  const data = await response.json();
  console.log(`\n${judul}`);
  console.log("HTTP       :", response.status);
  console.log("Keputusan  :", response.headers.get("x-ratf-decision"));
  console.log("Trust score:", data.ratf?.trust_score);
  console.log("Alasan     :", data.ratf?.reason_code);
  console.log("Respons    :", data);
}


await kirim("1. Request Node.js normal", {
  "X-Client-IP": "192.168.10.10",
  "X-Device-Id": "device-primary",
  "X-Hour-UTC": "10",
  "User-Agent": "MarketplaceNode/1.0"
});

await kirim("2. Token sama dari konteks yang sangat berbeda", {
  "X-Client-IP": "103.10.20.30",
  "X-Device-Id": "device-other",
  "X-Hour-UTC": "23",
  "User-Agent": "AutomationClient/4.0"
});
