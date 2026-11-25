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
    for (const key of ["GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","OPERATOR_OWNERS","OPERATOR_EMAILS","OPENAI_API_KEY","TRAIN_MODEL","CHAT_MODEL","TRAIN_EFFORT","CHAT_EFFORT","BOOKING_EFFORT","TRAIN_INPUT_USD_PER_M","TRAIN_OUTPUT_USD_PER_M","TRAIN_CACHED_USD_PER_M","CHAT_INPUT_USD_PER_M","CHAT_OUTPUT_USD_PER_M","CHAT_CACHED_USD_PER_M","INTEGRATION_ENCRYPTION_KEY","RESEND_API_KEY","RESEND_FROM","ENABLE_CHANNEL_WEBHOOKS","KAKAO_CALLBACK_HOSTS","ENABLE_AUTO_EMAIL","ENABLE_LIVE_EMAIL","ENABLE_BACKGROUND_WORKER","ENABLE_AUTO_CALENDAR","ENABLE_AUTO_REPORTS","VAPID_PUBLIC_KEY","VAPID_PRIVATE_KEY","VAPID_SUBJECT","ENABLE_AUTO_PUSH","ENABLE_LIVE_PUSH"] as const) {
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
  TRAIN_MODEL?: string;
  CHAT_MODEL?: string;
  TRAIN_EFFORT?: string;
  CHAT_EFFORT?: string;
  BOOKING_EFFORT?: string;
  TRAIN_INPUT_USD_PER_M?: string;
  TRAIN_OUTPUT_USD_PER_M?: string;
  TRAIN_CACHED_USD_PER_M?: string;
  CHAT_INPUT_USD_PER_M?: string;
  CHAT_OUTPUT_USD_PER_M?: string;
  CHAT_CACHED_USD_PER_M?: string;
  INTEGRATION_ENCRYPTION_KEY?: string;
  RESEND_API_KEY?: string;
  RESEND_FROM?: string;
  ENABLE_CHANNEL_WEBHOOKS?: string;
  KAKAO_CALLBACK_HOSTS?: string;
  ENABLE_AUTO_EMAIL?: string;
  ENABLE_LIVE_EMAIL?: string;
  ENABLE_BACKGROUND_WORKER?: string;
  ENABLE_AUTO_CALENDAR?: string;
  ENABLE_AUTO_REPORTS?: string;
  VAPID_PUBLIC_KEY?: string;
  VAPID_PRIVATE_KEY?: string;
  VAPID_SUBJECT?: string;
  ENABLE_AUTO_PUSH?: string;
  ENABLE_LIVE_PUSH?: string;
}
