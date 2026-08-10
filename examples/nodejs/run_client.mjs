async function send(label, headers) {
  const response = await fetch("http://127.0.0.1:5200/orders", {
    method: "POST",
    headers: {"Authorization": "Bearer node-app-token", "Content-Type": "application/json", "X-Scenario-Label": label, ...headers},
    body: JSON.stringify({item: "Smartphone", quantity: 1})
  });
  const body = await response.json();
  console.log(`\n${label}`);
  console.log("HTTP      :", response.status);
  console.log("Keputusan :", response.headers.get("x-ratf-decision"));
  console.log("Respons   :", body);
}

await send("Node normal", {"X-Client-IP": "192.168.10.10", "User-Agent": "MarketplaceNode/1.0", "X-Hour-UTC": "10"});
await send("Node konteks berbeda", {"X-Client-IP": "103.10.20.30", "User-Agent": "AutomationClient/4.0", "X-Device-Id": "device-other", "X-Hour-UTC": "23"});
