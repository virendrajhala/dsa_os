const SVG_NS = "http://www.w3.org/2000/svg";

export function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(key, String(value));
  }
  const kids = Array.isArray(children) ? children : children == null ? [] : [children];
  for (const child of kids) {
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}
