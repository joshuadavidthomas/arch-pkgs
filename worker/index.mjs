const AUTH_USER = "josh";
const encoder = new TextEncoder();

async function digest(value) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(value)));
}

async function equalSecrets(actual, expected) {
  const [actualDigest, expectedDigest] = await Promise.all([
    digest(actual),
    digest(expected),
  ]);

  let difference = 0;
  for (let index = 0; index < actualDigest.length; index += 1) {
    difference |= actualDigest[index] ^ expectedDigest[index];
  }
  return difference === 0;
}

async function isAuthorized(request, password) {
  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ") || !password) {
    return false;
  }

  let credentials;
  try {
    credentials = atob(authorization.slice(6));
  } catch {
    return false;
  }

  const separator = credentials.indexOf(":");
  if (separator === -1 || credentials.slice(0, separator) !== AUTH_USER) {
    return false;
  }

  return equalSecrets(credentials.slice(separator + 1), password);
}

function unauthorized() {
  return new Response("Authentication required.\n", {
    status: 401,
    headers: {
      "cache-control": "private, no-store",
      "www-authenticate": 'Basic realm="josh packages"',
    },
  });
}

function objectHeaders(object) {
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("accept-ranges", "bytes");
  headers.set("cache-control", "private, no-store");
  headers.set("etag", object.httpEtag);
  headers.set("last-modified", object.uploaded.toUTCString());
  return headers;
}

function parseRange(value, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(value);
  if (!match || (!match[1] && !match[2])) {
    return null;
  }

  if (!match[1]) {
    const suffix = Number(match[2]);
    if (!Number.isSafeInteger(suffix) || suffix <= 0 || size === 0) {
      return null;
    }
    const length = Math.min(suffix, size);
    return { offset: size - length, length };
  }

  const offset = Number(match[1]);
  if (!Number.isSafeInteger(offset) || offset >= size) {
    return null;
  }

  const requestedEnd = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isSafeInteger(requestedEnd) || requestedEnd < offset) {
    return null;
  }

  const end = Math.min(requestedEnd, size - 1);
  return { offset, length: end - offset + 1 };
}

function ifRangeMatches(value, object) {
  if (!value) {
    return true;
  }
  if (value.startsWith('"')) {
    return value === object.httpEtag;
  }

  const date = Date.parse(value);
  return Number.isFinite(date) && object.uploaded.getTime() <= date;
}

function rangeNotSatisfiable(object) {
  const headers = objectHeaders(object);
  headers.set("content-range", `bytes */${object.size}`);
  return new Response("Range not satisfiable.\n", { status: 416, headers });
}

async function serveHead(key, bucket) {
  const object = await bucket.head(key);
  if (object === null) {
    return new Response(null, { status: 404 });
  }

  const headers = objectHeaders(object);
  headers.set("content-length", String(object.size));
  return new Response(null, { status: 200, headers });
}

async function serveGet(request, key, bucket) {
  const rangeHeader = request.headers.get("range");
  if (!rangeHeader) {
    const object = await bucket.get(key);
    if (object === null) {
      return new Response("Object not found.\n", { status: 404 });
    }

    const headers = objectHeaders(object);
    headers.set("content-length", String(object.size));
    return new Response(object.body, { status: 200, headers });
  }

  const metadata = await bucket.head(key);
  if (metadata === null) {
    return new Response("Object not found.\n", { status: 404 });
  }

  const range = parseRange(rangeHeader, metadata.size);
  if (range === null) {
    return rangeNotSatisfiable(metadata);
  }

  if (!ifRangeMatches(request.headers.get("if-range"), metadata)) {
    const object = await bucket.get(key);
    if (object === null) {
      return new Response("Object not found.\n", { status: 404 });
    }

    const headers = objectHeaders(object);
    headers.set("content-length", String(object.size));
    return new Response(object.body, { status: 200, headers });
  }

  const object = await bucket.get(key, { range });
  if (object === null) {
    return new Response("Object not found.\n", { status: 404 });
  }
  if (object.httpEtag !== metadata.httpEtag) {
    const current = await bucket.get(key);
    if (current === null) {
      return new Response("Object not found.\n", { status: 404 });
    }

    const headers = objectHeaders(current);
    headers.set("content-length", String(current.size));
    return new Response(current.body, { status: 200, headers });
  }

  const headers = objectHeaders(object);
  const end = range.offset + range.length - 1;
  headers.set("content-range", `bytes ${range.offset}-${end}/${object.size}`);
  headers.set("content-length", String(range.length));
  return new Response(object.body, { status: 206, headers });
}

async function serve(request, bucket) {
  const key = new URL(request.url).pathname.slice(1);
  if (!key) {
    return new Response("Object not found.\n", { status: 404 });
  }

  if (request.method === "HEAD") {
    return serveHead(key, bucket);
  }
  return serveGet(request, key, bucket);
}

export async function handleRequest(request, env) {
  if (!(await isAuthorized(request, env.BASIC_AUTH_PASSWORD))) {
    return unauthorized();
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed.\n", {
      status: 405,
      headers: {
        allow: "GET, HEAD",
        "cache-control": "private, no-store",
      },
    });
  }

  return serve(request, env.PACKAGES);
}

export default {
  fetch: handleRequest,
};
