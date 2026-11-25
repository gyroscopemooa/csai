import { Container } from "@cloudflare/containers";

export class CsAiDevContainer extends Container {
  defaultPort = 8080;
  requiredPorts = [8080];
  sleepAfter = "10m";
  enableInternet = true;
  pingEndpoint = "/health";
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = env.CS_AI_APP.getByName("dev-singleton");
    await container.startAndWaitForPorts();
    return container.fetch(request);
  },
};

interface Env {
  CS_AI_APP: DurableObjectNamespace<CsAiDevContainer>;
}
