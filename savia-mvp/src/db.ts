import Database from "better-sqlite3";
import { mkdirSync } from "node:fs";

export type Lang = "uz" | "ru" | "en";
export const LANGS: Lang[] = ["uz", "ru", "en"];

export interface Translation {
  title: string;
  description: string;
}

export interface Shop {
  id: number;
  tg_id: number;
  slug: string;
  name: string;
  contact: string;
}

export interface Product {
  id: number;
  shop_id: number;
  category: string;
  price: number | null;
  currency: string;
  attributes: Record<string, string>;
  translations: Record<Lang, Translation>;
  photos: string[];
}

export const DATA_DIR = process.env.DATA_DIR ?? "data";
mkdirSync(`${DATA_DIR}/photos`, { recursive: true });

export const db = new Database(`${DATA_DIR}/savia.db`);
db.pragma("journal_mode = WAL");
db.exec(`
CREATE TABLE IF NOT EXISTS shops (
  id INTEGER PRIMARY KEY,
  tg_id INTEGER UNIQUE NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  contact TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  shop_id INTEGER NOT NULL REFERENCES shops(id),
  category TEXT NOT NULL DEFAULT '',
  price REAL,
  currency TEXT NOT NULL DEFAULT 'UZS',
  attributes TEXT NOT NULL DEFAULT '{}',
  translations TEXT NOT NULL,
  photo TEXT
);
CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL,
  question TEXT NOT NULL,
  answered INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
`);

const parsePhotos = (v: string | null): string[] =>
  !v ? [] : v.startsWith("[") ? JSON.parse(v) : [v];

const toProduct = (r: any): Product => ({
  ...r,
  attributes: JSON.parse(r.attributes),
  translations: JSON.parse(r.translations),
  photos: parsePhotos(r.photo),
});

export function getOrCreateShop(tgId: number, displayName: string): Shop {
  const found = db.prepare("SELECT * FROM shops WHERE tg_id = ?").get(tgId) as Shop | undefined;
  if (found) return found;
  const base = displayName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `shop-${Math.random().toString(36).slice(2, 7)}`;
  let slug = base;
  for (let i = 2; db.prepare("SELECT 1 FROM shops WHERE slug = ?").get(slug); i++) slug = `${base}-${i}`;
  const id = db
    .prepare("INSERT INTO shops (tg_id, slug, name) VALUES (?, ?, ?)")
    .run(tgId, slug, displayName).lastInsertRowid;
  return db.prepare("SELECT * FROM shops WHERE id = ?").get(id) as Shop;
}

export const getShopBySlug = (slug: string) =>
  db.prepare("SELECT * FROM shops WHERE slug = ?").get(slug) as Shop | undefined;

export const getShopById = (id: number) =>
  db.prepare("SELECT * FROM shops WHERE id = ?").get(id) as Shop | undefined;

export function updateShop(id: number, fields: Partial<Pick<Shop, "name" | "contact">>) {
  if (fields.name !== undefined) db.prepare("UPDATE shops SET name = ? WHERE id = ?").run(fields.name, id);
  if (fields.contact !== undefined) db.prepare("UPDATE shops SET contact = ? WHERE id = ?").run(fields.contact, id);
}

export function addProduct(p: Omit<Product, "id">): Product {
  const id = db
    .prepare(
      "INSERT INTO products (shop_id, category, price, currency, attributes, translations, photo) VALUES (?,?,?,?,?,?,?)",
    )
    .run(p.shop_id, p.category, p.price, p.currency, JSON.stringify(p.attributes), JSON.stringify(p.translations), p.photos.length ? JSON.stringify(p.photos) : null)
    .lastInsertRowid;
  return getProduct(Number(id))!;
}

export const getProduct = (id: number) => {
  const r = db.prepare("SELECT * FROM products WHERE id = ?").get(id);
  return r ? toProduct(r) : undefined;
};

export const listProducts = (shopId: number) =>
  db.prepare("SELECT * FROM products WHERE shop_id = ? ORDER BY id DESC").all(shopId).map(toProduct);

export function deleteProduct(id: number, shopId: number): boolean {
  return db.prepare("DELETE FROM products WHERE id = ? AND shop_id = ?").run(id, shopId).changes > 0;
}

export function logQuestion(productId: number, question: string, answered: boolean) {
  db.prepare("INSERT INTO questions (product_id, question, answered) VALUES (?,?,?)").run(
    productId,
    question,
    answered ? 1 : 0,
  );
}
