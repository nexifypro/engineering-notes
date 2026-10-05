/**
 * Prisma client extension that applies the tenant to every query.
 *
 * Every operation runs inside an interactive transaction that first executes
 * `SET LOCAL app.tenant_id`, so RLS policies see the tenant and the setting dies with the
 * transaction. The tenant comes from request-scoped AsyncLocalStorage, populated by the
 * auth middleware from the verified token, never from the caller's arguments.
 *
 * Illustrative; mirrors the row-level-security example in prisma/prisma-client-extensions.
 */
import { AsyncLocalStorage } from "node:async_hooks";
import { Prisma, PrismaClient } from "@prisma/client";

export const tenantContext = new AsyncLocalStorage<{ tenantId: string }>();

export function withTenant(base: PrismaClient) {
  return base.$extends({
    query: {
      $allModels: {
        async $allOperations({ args, query }) {
          const ctx = tenantContext.getStore();
          if (!ctx) throw new Error("database access without a tenant in context");
          const [, result] = await base.$transaction([
            base.$executeRaw`SELECT set_config('app.tenant_id', ${ctx.tenantId}, TRUE)`,
            query(args),
          ]);
          return result;
        },
      },
    },
  });
}

// In the request pipeline:
//   app.use((req, res, next) => tenantContext.run({ tenantId: req.auth.tenantId }, next));
// In a worker:
//   tenantContext.run({ tenantId: job.data.tenantId }, () => handle(job));
