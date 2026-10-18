import assert from "node:assert/strict";
import test from "node:test";
import { convertLink } from "../lib/convertLink.mjs";

const types = ["rapporter", "rattsliga-dokument/proposition"];

test("converts government roots, collections and pages", () => {
  for (const [input, expected] of [
    ["https://www.regeringen.se/", "https://g0v.se/api/items.json"],
    ["gov.se", "https://g0v.se/api/items.json"],
    ["www.gov.se/rapporter/", "https://g0v.se/rapporter.json"],
    ["http://regeringen.se/rattsliga-dokument/proposition/", "https://g0v.se/rattsliga-dokument/proposition.json"],
    ["https://regeringen.se/rapporter/2026/ett-betankande/", "https://g0v.se/rapporter/2026/ett-betankande.md"],
    ["https://regeringen.se/artiklar/om-rapporter/", "https://g0v.se/artiklar/om-rapporter.md"],
    [" HTTPS://WWW.REGERINGEN.SE/rapporter/ ", "https://g0v.se/rapporter.json"],
  ]) {
    assert.equal(convertLink(input, types)?.newLink, expected, input);
  }
});

test("rejects lookalike hosts, credentials, nonstandard ports and schemes", () => {
  for (const input of [
    "https://regeringen.se.evil.test/",
    "regeringen.seevil.test/",
    "https://gov.se.evil.test/",
    "https://regeringen.se@evil.test/",
    "https://user:password@regeringen.se/",
    "https://regeringen.se:8080/",
    "https://evil.test/regeringen.se/",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "ftp://regeringen.se/rapporter/",
    "not a URL", "", "   ",
  ]) {
    assert.equal(convertLink(input, types), null, input);
  }
});

test("encodes hostile path text and always keeps the g0v.se origin", () => {
  for (const path of [
    '/artiklar/<img src=x onerror="alert(1)">/',
    "/artiklar/%3Csvg%20onload%3Dalert(1)%3E/",
    "/%2F%2Fevil.test/",
    "//evil.test/path/",
    "/artiklar/ett-betänkande/",
  ]) {
    const converted = convertLink("https://regeringen.se" + path, types);
    assert.ok(converted, path);
    const target = new URL(converted.newLink);
    assert.equal(target.origin, "https://g0v.se", path);
    assert.equal(target.username, "", path);
    assert.doesNotMatch(converted.newLink, /[<>"\s]/, path);
  }
  assert.equal(convertLink("https://regeringen.se/%2F%2Fevil.test/", types).newLink,
    "https://g0v.se/%2F%2Fevil.test.md");
  assert.equal(convertLink("https://regeringen.se/artiklar/%C3%A5/", types).newLink,
    "https://g0v.se/artiklar/%C3%A5.md");
  assert.equal(convertLink("https://regeringen.se/invalid%escape/", types), null);
});

test("uses the canonical page path without query strings or fragments", () => {
  assert.equal(convertLink("https://regeringen.se/rapporter/?query=test#result", types).newLink,
    "https://g0v.se/rapporter.json");
});
