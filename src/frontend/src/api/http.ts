/**
 * The low-level HTTP plumbing every API module builds its calls on.
 *
 * Nothing here knows about a resource of the backend -- the hollow's own
 * `client.ts` and each plugin's own API module all build on this, so none of
 * them has to repeat it.
 */

/** An error the backend answered with, carrying its reason. */
export class ApiError extends Error {
  constructor(
    message: string,
    /** The HTTP status the backend answered with. */
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Percent-encode a hollow-relative path, segment by segment. */
export function encodePath(path: string): string {
  return path
    .split('/')
    .filter((segment) => segment.length > 0)
    .map(encodeURIComponent)
    .join('/')
}

/** Read the reason out of a failed response, whatever shape it arrived in. */
async function reasonOf(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) return body.detail.map((item: any) => item?.msg).join(', ')
  } catch {
    /* a body that is not JSON tells us nothing more than the status does */
  }
  return `Error ${response.status}`
}

/** Send one request and parse its answer, raising ApiError on any failure. */
export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch {
    throw new ApiError('The server is not answering', 0)
  }
  if (!response.ok) {
    throw new ApiError(await reasonOf(response), response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Send a JSON body. */
export function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}
