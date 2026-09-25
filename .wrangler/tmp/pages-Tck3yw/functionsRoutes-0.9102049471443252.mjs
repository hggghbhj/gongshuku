import { onRequestGet as __api_check_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/check.js"
import { onRequestOptions as __api_check_js_onRequestOptions } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/check.js"
import { onRequestGet as __api_cron_health_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/cron-health.js"
import { onRequestOptions as __api_cron_health_js_onRequestOptions } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/cron-health.js"
import { onRequestPost as __api_cron_health_js_onRequestPost } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/cron-health.js"
import { onRequestGet as __api_health_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/health.js"
import { onRequestGet as __api_healthmap_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/healthmap.js"
import { onRequestOptions as __api_healthmap_js_onRequestOptions } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/healthmap.js"
import { onRequestGet as __api_pdf_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/pdf.js"
import { onRequestHead as __api_pdf_js_onRequestHead } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/pdf.js"
import { onRequestOptions as __api_pdf_js_onRequestOptions } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/pdf.js"
import { onRequestGet as __api_report_js_onRequestGet } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/report.js"
import { onRequestOptions as __api_report_js_onRequestOptions } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/report.js"
import { onRequestPost as __api_report_js_onRequestPost } from "/home/user/Doubao/chats/38443037035314434/gsk-cloud/functions/api/report.js"

export const routes = [
    {
      routePath: "/api/check",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_check_js_onRequestGet],
    },
  {
      routePath: "/api/check",
      mountPath: "/api",
      method: "OPTIONS",
      middlewares: [],
      modules: [__api_check_js_onRequestOptions],
    },
  {
      routePath: "/api/cron-health",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_cron_health_js_onRequestGet],
    },
  {
      routePath: "/api/cron-health",
      mountPath: "/api",
      method: "OPTIONS",
      middlewares: [],
      modules: [__api_cron_health_js_onRequestOptions],
    },
  {
      routePath: "/api/cron-health",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_cron_health_js_onRequestPost],
    },
  {
      routePath: "/api/health",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_health_js_onRequestGet],
    },
  {
      routePath: "/api/healthmap",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_healthmap_js_onRequestGet],
    },
  {
      routePath: "/api/healthmap",
      mountPath: "/api",
      method: "OPTIONS",
      middlewares: [],
      modules: [__api_healthmap_js_onRequestOptions],
    },
  {
      routePath: "/api/pdf",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_pdf_js_onRequestGet],
    },
  {
      routePath: "/api/pdf",
      mountPath: "/api",
      method: "HEAD",
      middlewares: [],
      modules: [__api_pdf_js_onRequestHead],
    },
  {
      routePath: "/api/pdf",
      mountPath: "/api",
      method: "OPTIONS",
      middlewares: [],
      modules: [__api_pdf_js_onRequestOptions],
    },
  {
      routePath: "/api/report",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_report_js_onRequestGet],
    },
  {
      routePath: "/api/report",
      mountPath: "/api",
      method: "OPTIONS",
      middlewares: [],
      modules: [__api_report_js_onRequestOptions],
    },
  {
      routePath: "/api/report",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_report_js_onRequestPost],
    },
  ]