const GOVERNMENT_HOSTS = new Set([
  "regeringen.se",
  "www.regeringen.se",
  "gov.se",
  "www.gov.se",
]);

export function convertLink(input, types) {
  const link = input.trim();
  if (!link) return null;

  try {
    const protocol = link.match(/^https?:\/\//i)?.[0] ?? "";
    const source = new URL(protocol ? link : `https://${link}`);
    if (
      !["http:", "https:"].includes(source.protocol) ||
      !GOVERNMENT_HOSTS.has(source.hostname) ||
      source.username || source.password || source.port
    ) {
      return null;
    }

    const path = source.pathname.replace(/\/$/, "");
    // Encode each segment without turning an escaped slash into a path separator.
    const encodedPath = path.split("/").map(
      segment => encodeURIComponent(decodeURIComponent(segment))
    ).join("/");
    const addedPrefix = "https://g0v.se";
    const addedSuffix = !path
      ? "/api/items.json"
      : types.includes(path.slice(1)) ? ".json" : ".md";

    return {
      newLink: addedPrefix + encodedPath + addedSuffix,
      removedPrefix: protocol + source.host,
      addedPrefix,
      middle: path,
      removedSuffix: link.endsWith("/") ? "/" : "",
      addedSuffix,
    };
  } catch {
    // Invalid URLs or malformed percent escapes cannot produce a link.
    return null;
  }
}
