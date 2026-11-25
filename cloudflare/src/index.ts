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
    const container = env.CS_AI_APP.getByName("dev-singleton-oauth-v2");
    const envVars: Record<string, string> = {
      APP_URL: new URL(request.url).origin,
      SHARED_TEST_MODE: "1",
      DEMO_MODE: "1",
    };
    for (const key of ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPERATOR_OWNERS", "OPERATOR_EMAILS", "OPENAI_API_KEY"] as const) {
      if (env[key]) envVars[key] = env[key];
    }
    await container.startAndWaitForPorts({ startOptions: { envVars } });
    return container.fetch(request);
  },
};

interface Env {
  CS_AI_APP: DurableObjectNamespace<CsAiDevContainer>;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  OPERATOR_OWNERS?: string;
  OPERATOR_EMAILS?: string;
  OPENAI_API_KEY?: string;
}
