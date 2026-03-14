import { spawn } from "node:child_process";
import os from "node:os";
import path from "node:path";

/**
 * @typedef {Record<string, any>} QueryParams
 */

/**
 * @typedef {Object} BridgeResponse
 * @property {boolean} ok Whether the Python bridge completed successfully.
 * @property {string} interface Interface name invoked on the Python side.
 * @property {QueryParams} params Normalized request parameters.
 * @property {boolean} cache_hit Whether the result came from SQLite cache.
 * @property {number} estimated_row_bytes Estimated average UTF-8 byte size per row.
 * @property {number} max_rows Maximum allowed rows under the payload limit.
 * @property {number} requested_rows Row count before density reduction.
 * @property {number} returned_rows Row count returned after density reduction.
 * @property {number} sampling_step Even sampling step applied per day. `1` means no reduction.
 * @property {Array<Record<string, any>>} rows Returned data rows.
 */

/**
 * @typedef {Object} ClientOptions
 * @property {string} [pythonBin] Python executable. Defaults to `py` on Windows and `python3` on Linux.
 * @property {string} [dbPath] SQLite database path.
 * @property {number} [maxBytes] Maximum UTF-8 response size for the row payload.
 * @property {string} [projectRoot] Project root used to locate the Python bridge package.
 * @property {NodeJS.ProcessEnv} [env] Extra environment variables passed to the Python process.
 */

/**
 * Interface names grouped by business type for dependency injection.
 */
export const INTERFACE_GROUPS = {
  stock: ["stock_zh_a_spot", "stock_zh_a_hist", "stock_intraday_em", "stock_bid_ask_em"],
  futures: ["futures_zh_spot", "futures_zh_hist", "match_main_contract", "futures_basis"],
  fund: ["fund_meta", "fund_etf_market", "fund_open_info"],
  macro: ["macro_china_all"],
  commodity: ["commodity_basis", "spot_sge"],
  bond: ["bond_zh_hs_market", "bond_zh_hs_cov_market", "bond_cb_meta"],
  board: ["stock_board_industry", "stock_board_concept"],
};

/**
 * Create a client that exposes AKShare-like functions for Node callers.
 *
 * @param {ClientOptions} [options] Client configuration.
 * @returns {AkshareNodeClient} Configured client instance.
 */
export function createClient(options = {}) {
  return new AkshareNodeClient(options);
}

/**
 * Create grouped method sets for category-based injection.
 *
 * @param {ClientOptions} [options] Client configuration.
 * @returns {ReturnType<AkshareNodeClient["byType"]>} Grouped client methods.
 */
export function createTypedClient(options = {}) {
  return createClient(options).byType();
}

/**
 * Node client for the Python AKShare bridge.
 */
export class AkshareNodeClient {
  /**
   * @param {ClientOptions} [options]
   */
  constructor(options = {}) {
    this.projectRoot = options.projectRoot || process.cwd();
    this.pythonBin = options.pythonBin || (os.platform() === "win32" ? "py" : "python3");
    this.dbPath =
      options.dbPath || process.env.AKSHARE_NODE_DB_PATH || path.join(this.projectRoot, "data", "akshare_cache.sqlite");
    this.maxBytes = options.maxBytes || Number(process.env.AKSHARE_NODE_MAX_BYTES || 2000);
    this.env = { ...process.env, ...options.env };
  }

  /**
   * Return grouped method sets keyed by business type.
   *
   * @returns {{
   *   client: AkshareNodeClient,
   *   stock: Record<string, Function>,
   *   futures: Record<string, Function>,
   *   fund: Record<string, Function>,
   *   macro: Record<string, Function>,
   *   commodity: Record<string, Function>,
   *   bond: Record<string, Function>,
   *   board: Record<string, Function>
   * }} Grouped method facade.
   */
  byType() {
    const groups = { client: this };
    for (const [groupName, methods] of Object.entries(INTERFACE_GROUPS)) {
      groups[groupName] = Object.fromEntries(methods.map((methodName) => [methodName, this[methodName].bind(this)]));
    }
    return groups;
  }

  /**
   * Invoke the Python bridge with a named interface.
   *
   * @param {string} interfaceName Interface name implemented by the Python bridge.
   * @param {QueryParams} [params={}] Interface parameters.
   * @returns {Promise<BridgeResponse>} Standardized bridge response.
   */
  async invoke(interfaceName, params = {}) {
    const input = JSON.stringify({
      interface: interfaceName,
      params,
      db_path: this.dbPath,
      max_bytes: this.maxBytes,
    });
    const pythonPath = path.join(this.projectRoot, "python");

    return new Promise((resolve, reject) => {
      const child = spawn(this.pythonBin, ["-m", "akshare_node_bridge.cli"], {
        cwd: this.projectRoot,
        env: {
          ...this.env,
          PYTHONIOENCODING: this.env.PYTHONIOENCODING || "utf-8",
          PYTHONUTF8: this.env.PYTHONUTF8 || "1",
          PYTHONPATH: this.env.PYTHONPATH ? `${pythonPath}${path.delimiter}${this.env.PYTHONPATH}` : pythonPath,
        },
        stdio: ["pipe", "pipe", "pipe"],
      });

      let stdout = "";
      let stderr = "";

      child.stdout.on("data", (chunk) => {
        stdout += chunk.toString();
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk.toString();
      });
      child.on("error", reject);

      child.on("close", (code) => {
        if (!stdout.trim()) {
          reject(new Error(`Python bridge produced no output. Exit code: ${code}. stderr: ${stderr}`));
          return;
        }

        let parsed;
        try {
          parsed = JSON.parse(stdout);
        } catch (error) {
          reject(new Error(`Failed to parse Python bridge output: ${error}. stdout: ${stdout}. stderr: ${stderr}`));
          return;
        }

        if (parsed.ok) {
          resolve(parsed);
          return;
        }

        reject(new Error(parsed?.error?.message || stderr || `Python bridge failed with exit code ${code}`));
      });

      child.stdin.write(input);
      child.stdin.end();
    });
  }

  /**
   * Get A-share real-time market data.
   *
   * @param {QueryParams} [params={}] Supports `symbol` for filtering a single stock.
   * @returns {Promise<BridgeResponse>} Real-time A-share rows.
   */
  async stock_zh_a_spot(params = {}) { return this.invoke("stock_zh_a_spot", params); }

  /**
   * Get A-share historical data. Minute periods will be reduced evenly if the payload exceeds the byte limit.
   *
   * @param {QueryParams} [params={}] Supports `symbol`, `period`, `start_date`, `end_date`, and `adjust`.
   * @returns {Promise<BridgeResponse>} Historical A-share rows.
   */
  async stock_zh_a_hist(params = {}) { return this.invoke("stock_zh_a_hist", params); }

  /**
   * Get intraday trade details for a single A-share symbol.
   *
   * @param {QueryParams} params Supports `symbol`.
   * @returns {Promise<BridgeResponse>} Intraday rows.
   */
  async stock_intraday_em(params) { return this.invoke("stock_intraday_em", params); }

  /**
   * Get order book and bid/ask data for a single A-share symbol.
   *
   * @param {QueryParams} params Supports `symbol`.
   * @returns {Promise<BridgeResponse>} Bid/ask rows.
   */
  async stock_bid_ask_em(params) { return this.invoke("stock_bid_ask_em", params); }

  /**
   * Get futures real-time market data.
   *
   * @param {QueryParams} [params={}] Supports `symbol`, `market`, and `adjust`.
   * @returns {Promise<BridgeResponse>} Futures real-time rows.
   */
  async futures_zh_spot(params = {}) { return this.invoke("futures_zh_spot", params); }

  /**
   * Get futures historical data.
   *
   * @param {QueryParams} [params={}] Supports `symbol`, `period`, and optional `source`.
   * @returns {Promise<BridgeResponse>} Futures historical rows.
   */
  async futures_zh_hist(params = {}) { return this.invoke("futures_zh_hist", params); }

  /**
   * Get main contract mappings by exchange.
   *
   * @param {QueryParams} [params={}] Supports `symbol`. `exchange` is also accepted as an alias for compatibility.
   * @returns {Promise<BridgeResponse>} Main contract rows.
   */
  async match_main_contract(params = {}) { return this.invoke("match_main_contract", params); }

  /**
   * Get futures basis and spot-related analysis data.
   *
   * @param {QueryParams} [params={}] Supports `mode`, `date`, and `symbol`.
   * @returns {Promise<BridgeResponse>} Basis rows.
   */
  async futures_basis(params = {}) { return this.invoke("futures_basis", params); }

  /**
   * Get fund metadata or purchase status data.
   *
   * @param {QueryParams} [params={}] Supports `mode`.
   * @returns {Promise<BridgeResponse>} Fund metadata rows.
   */
  async fund_meta(params = {}) { return this.invoke("fund_meta", params); }

  /**
   * Get ETF market data.
   *
   * @param {QueryParams} [params={}] Supports `mode`, `symbol`, `period`, `start_date`, `end_date`, and `adjust`.
   * @returns {Promise<BridgeResponse>} ETF rows.
   */
  async fund_etf_market(params = {}) { return this.invoke("fund_etf_market", params); }

  /**
   * Get open fund data such as NAV trend or rankings.
   *
   * @param {QueryParams} [params={}] Supports `symbol` and `indicator`.
   * @returns {Promise<BridgeResponse>} Open fund rows.
   */
  async fund_open_info(params = {}) { return this.invoke("fund_open_info", params); }

  /**
   * Get merged China macroeconomic datasets in a single call.
   *
   * @param {QueryParams} [params={}] Supports `datasets` for selecting a subset of macro datasets.
   * @returns {Promise<BridgeResponse>} Flattened macro rows tagged by `dataset`.
   */
  async macro_china_all(params = {}) { return this.invoke("macro_china_all", params); }

  /**
   * Get commodity spot and basis data.
   *
   * @param {QueryParams} [params={}] Supports `mode`, `symbol`, and `date`.
   * @returns {Promise<BridgeResponse>} Commodity rows.
   */
  async commodity_basis(params = {}) { return this.invoke("commodity_basis", params); }

  /**
   * Get Shanghai Gold Exchange quote or historical spot data.
   *
   * @param {QueryParams} [params={}] Supports `mode` and `symbol`.
   * @returns {Promise<BridgeResponse>} SGE rows.
   */
  async spot_sge(params = {}) { return this.invoke("spot_sge", params); }

  /**
   * Get bond market data from Shanghai and Shenzhen exchanges.
   *
   * @param {QueryParams} [params={}] Supports `mode` and `symbol`.
   * @returns {Promise<BridgeResponse>} Bond rows.
   */
  async bond_zh_hs_market(params = {}) { return this.invoke("bond_zh_hs_market", params); }

  /**
   * Get convertible bond market data from Shanghai and Shenzhen exchanges.
   *
   * @param {QueryParams} [params={}] Supports `mode` and `symbol`.
   * @returns {Promise<BridgeResponse>} Convertible bond rows.
   */
  async bond_zh_hs_cov_market(params = {}) { return this.invoke("bond_zh_hs_cov_market", params); }

  /**
   * Get convertible bond metadata.
   *
   * @param {QueryParams} [params={}] Supports `mode` and `symbol`.
   * @returns {Promise<BridgeResponse>} Convertible bond metadata rows.
   */
  async bond_cb_meta(params = {}) { return this.invoke("bond_cb_meta", params); }

  /**
   * Get industry board list or historical data.
   *
   * @param {QueryParams} [params={}] Supports `mode`, `symbol`, `start_date`, `end_date`, `period`, and `adjust`.
   * @returns {Promise<BridgeResponse>} Industry board rows.
   */
  async stock_board_industry(params = {}) { return this.invoke("stock_board_industry", params); }

  /**
   * Get concept board list or historical data.
   *
   * @param {QueryParams} [params={}] Supports `mode`, `symbol`, `start_date`, `end_date`, `period`, and `adjust`.
   * @returns {Promise<BridgeResponse>} Concept board rows.
   */
  async stock_board_concept(params = {}) { return this.invoke("stock_board_concept", params); }
}
