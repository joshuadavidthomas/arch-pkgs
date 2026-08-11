import assert from "node:assert/strict";
import test from "node:test";

import { handleRequest } from "./index.mjs";

const password = "correct horse battery staple";
const authorization = `Basic ${Buffer.from(`josh:${password}`).toString("base64")}`;
const uploaded = new Date("2026-08-10T00:00:00Z");

function object(body = "package") {
  return {
    body,
    httpEtag: '"etag"',
    size: body.length,
    uploaded,
    writeHttpMetadata(headers) {
      headers.set("content-type", "application/octet-stream");
      headers.set("cache-control", "public, max-age=31536000, immutable");
    },
  };
}

function env(overrides = {}) {
  return {
    BASIC_AUTH_PASSWORD: password,
    PACKAGES: {
      async get() {
        return object();
      },
      async head() {
        return object();
      },
    },
    ...overrides,
  };
}

function request(method = "GET", headers = {}) {
  return new Request("https://pkgs.joshthomas.dev/arch/josh/os/x86_64/josh.db", {
    method,
    headers,
  });
}

test("rejects missing and incorrect credentials", async () => {
  const missing = await handleRequest(request(), env());
  const incorrect = await handleRequest(
    request("GET", {
      authorization: `Basic ${Buffer.from("josh:wrong").toString("base64")}`,
    }),
    env(),
  );

  assert.equal(missing.status, 401);
  assert.equal(incorrect.status, 401);
  assert.match(missing.headers.get("www-authenticate"), /^Basic /);
});

test("serves an authenticated object without public caching", async () => {
  const response = await handleRequest(
    request("GET", { authorization }),
    env(),
  );

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "package");
  assert.equal(response.headers.get("cache-control"), "private, no-store");
  assert.equal(response.headers.get("content-length"), "7");
});

test("serves metadata for HEAD requests", async () => {
  const response = await handleRequest(
    request("HEAD", { authorization }),
    env(),
  );

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
  assert.equal(response.headers.get("content-length"), "7");
});

for (const { header, expected, contentRange } of [
  {
    header: "bytes=1-3",
    expected: { offset: 1, length: 3 },
    contentRange: "bytes 1-3/7",
  },
  {
    header: "bytes=4-",
    expected: { offset: 4, length: 3 },
    contentRange: "bytes 4-6/7",
  },
  {
    header: "bytes=-3",
    expected: { offset: 4, length: 3 },
    contentRange: "bytes 4-6/7",
  },
]) {
  test(`normalizes ${header} and returns a partial response`, async () => {
    let range;
    const packages = {
      async head() {
        return object();
      },
      async get(_key, options) {
        range = options.range;
        return { ...object("ack"), size: 7 };
      },
    };

    const response = await handleRequest(
      request("GET", { authorization, range: header }),
      env({ PACKAGES: packages }),
    );

    assert.deepEqual(range, expected);
    assert.equal(response.status, 206);
    assert.equal(response.headers.get("content-range"), contentRange);
    assert.equal(response.headers.get("content-length"), String(expected.length));
  });
}

test("rejects malformed and unsatisfiable ranges", async () => {
  for (const range of ["bytes=", "bytes=8-", "bytes=4-2", "bytes=0-1,4-5"]) {
    const response = await handleRequest(
      request("GET", { authorization, range }),
      env(),
    );

    assert.equal(response.status, 416, range);
    assert.equal(response.headers.get("content-range"), "bytes */7");
  }
});

test("ignores a range when If-Range names an older object", async () => {
  let options;
  const packages = {
    async head() {
      return object();
    },
    async get(_key, value) {
      options = value;
      return object();
    },
  };

  const response = await handleRequest(
    request("GET", {
      authorization,
      range: "bytes=1-3",
      "if-range": '"old-etag"',
    }),
    env({ PACKAGES: packages }),
  );

  assert.equal(response.status, 200);
  assert.equal(options, undefined);
  assert.equal(response.headers.get("content-length"), "7");
});

test("restarts a ranged read when the object changes", async () => {
  let calls = 0;
  const packages = {
    async head() {
      return object();
    },
    async get(_key, options) {
      calls += 1;
      if (options) {
        return { ...object("ack"), httpEtag: '"new-etag"', size: 7 };
      }
      return { ...object(), httpEtag: '"new-etag"' };
    },
  };

  const response = await handleRequest(
    request("GET", { authorization, range: "bytes=1-3" }),
    env({ PACKAGES: packages }),
  );

  assert.equal(response.status, 200);
  assert.equal(calls, 2);
  assert.equal(response.headers.get("content-length"), "7");
});

test("allows only reads and hides missing objects", async () => {
  const missingPackages = {
    async get() {
      return null;
    },
  };
  const missing = await handleRequest(
    request("GET", { authorization }),
    env({ PACKAGES: missingPackages }),
  );
  const post = await handleRequest(
    request("POST", { authorization }),
    env(),
  );

  assert.equal(missing.status, 404);
  assert.equal(post.status, 405);
  assert.equal(post.headers.get("allow"), "GET, HEAD");
});
