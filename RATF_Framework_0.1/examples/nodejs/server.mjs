import http from "node:http";
import crypto from "node:crypto";

const port = Number(process.env.PORT || 5200);
const evaluationUrl = process.env.RATF_EVALUATION_URL || "http://127.0.0.1:5100/access/v1/evaluation";
const evaluationKey = process.env.RATF_EVALUATION_KEY || "local-authzen-service-key";
const applicationToken = process.env.NODE_EXAMPLE_TOKEN || "node-app-token";
const policyId = process.env.RATF_POLICY_ID || "important-api";

async function evaluate(req) {
  const requestId = req.headers["x-request-id"] || crypto.randomUUID();
  const payload = {
    subject: {
      type: "user",
      id: "customer-001",
      properties: {
        client_id: "marketplace-node",
        scopes: ["orders:write"],
        family_id: "node-customer-001",
        issued_ip: "192.168.10.10",
        issued_user_agent: "MarketplaceNode/1.0",
        issued_hour_utc: 10
      }
    },
    resource: {type: "endpoint", id: "/orders", properties: {transactional: true}},
    action: {name: "POST", properties: {required_scope: "orders:write"}},
    context: {
      source_ip: req.headers["x-client-ip"] || "192.168.10.10",
      user_agent: req.headers["user-agent"] || "MarketplaceNode/1.0",
      client_id: "marketplace-node",
      device_id: req.headers["x-device-id"] || "device-primary",
      hour_utc: Number(req.headers["x-hour-utc"] || 10),
      policy_id: policyId,
      scenario_label: req.headers["x-scenario-label"] || "node-request"
    }
  };
  const response = await fetch(evaluationUrl, {
    method: "POST",
    headers: {"Authorization": `Bearer ${evaluationKey}`, "Content-Type": "application/json", "X-Request-ID": requestId},
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Evaluation service returned HTTP ${response.status}`);
  return response.json();
}

const server = http.createServer(async (req, res) => {
  if (req.method !== "POST" || req.url !== "/orders") {
    res.writeHead(404, {"Content-Type": "application/json"});
    return res.end(JSON.stringify({error: "not_found"}));
  }
  if (req.headers.authorization !== `Bearer ${applicationToken}`) {
    res.writeHead(401, {"Content-Type": "application/json"});
    return res.end(JSON.stringify({error: "application_token_invalid"}));
  }
  try {
    const evaluation = await evaluate(req);
    const ratf = evaluation.context.ratf;
    if (!evaluation.decision) {
      const status = ratf.decision === "verify" ? 401 : 403;
      res.writeHead(status, {"Content-Type": "application/json", "X-RATF-Decision": ratf.decision});
      return res.end(JSON.stringify({status: "not_forwarded", ...ratf}));
    }
    res.writeHead(201, {"Content-Type": "application/json", "X-RATF-Decision": ratf.decision});
    return res.end(JSON.stringify({order_id: `node_${crypto.randomUUID().slice(0, 8)}`, status: "created", ratf}));
  } catch (error) {
    res.writeHead(503, {"Content-Type": "application/json"});
    return res.end(JSON.stringify({error: "evaluation_service_unavailable", message: error.message}));
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Node.js example: http://127.0.0.1:${port}/orders`);
});
