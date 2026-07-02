/* eslint-disable */
// Generated lightweight client helpers from FastAPI OpenAPI.
import { apiDelete, apiGet, apiPatch, apiPost } from "../../../apps/web/lib/api"
import type { paths } from "./schema"

type OperationResponse<T> = T extends { response: infer R } ? R : never
type OperationBody<T> = T extends { body: infer B } ? B : never
type PathWith<Method extends string> = {
  [Path in keyof paths & string]: Method extends keyof paths[Path] ? Path : never
}[keyof paths & string]

type JsonInit = Omit<RequestInit, "body" | "method">

export function get<Path extends PathWith<"get">>(
  path: Path,
  init?: JsonInit,
): Promise<OperationResponse<paths[Path]["get"]>> {
  return apiGet(path, init) as Promise<OperationResponse<paths[Path]["get"]>>
}

export function post<Path extends PathWith<"post">>(
  path: Path,
  body?: OperationBody<paths[Path]["post"]>,
  init?: JsonInit,
): Promise<OperationResponse<paths[Path]["post"]>> {
  return apiPost(path, { ...init, body: body === undefined ? undefined : JSON.stringify(body) }) as Promise<OperationResponse<paths[Path]["post"]>>
}

export function patch<Path extends PathWith<"patch">>(
  path: Path,
  body?: OperationBody<paths[Path]["patch"]>,
  init?: JsonInit,
): Promise<OperationResponse<paths[Path]["patch"]>> {
  return apiPatch(path, { ...init, body: body === undefined ? undefined : JSON.stringify(body) }) as Promise<OperationResponse<paths[Path]["patch"]>>
}

export function del<Path extends PathWith<"delete">>(
  path: Path,
  init?: JsonInit,
): Promise<OperationResponse<paths[Path]["delete"]>> {
  return apiDelete(path, init) as Promise<OperationResponse<paths[Path]["delete"]>>
}
