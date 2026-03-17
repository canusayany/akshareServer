import { createClient } from "./index.js";

/**
 * @typedef {import("./index.js").AkshareNodeClient} AkshareNodeClient
 */

/**
 * @typedef {Object} ToolDefinition
 * @property {string} name Tool name. Matches the Python bridge interface name.
 * @property {string} description Short tool description.
 * @property {string[]} params Common parameter names.
 */

const TOOL_DEFINITIONS = [
  ["stock_zh_a_spot", "Get A-share real-time market data", ["symbol"]],
  ["stock_zh_a_hist", "Get A-share historical market data", ["symbol", "period", "start_date", "end_date", "adjust"]],
  ["stock_intraday_em", "Get A-share intraday trades", ["symbol"]],
  ["stock_bid_ask_em", "Get A-share order book data", ["symbol"]],
  ["stock_index_zh_hist", "Get stock index daily K-line (e.g. 沪深300, 中证500)", ["symbol", "start_date", "end_date"]],
  ["stock_financial_abstract", "Get stock financial abstract", ["symbol", "year"]],
  ["stock_yjbb_em", "Get performance report (业绩快报)", ["date"]],
  ["stock_yjyg_em", "Get performance forecast (业绩预告)", ["date"]],
  ["futures_zh_spot", "Get futures real-time market data", ["symbol", "market", "adjust"]],
  ["option_finance_board", "Get financial options board (50ETF/300ETF)", ["symbol", "end_month"]],
  ["option_current_em", "Get options current day market", []],
  ["option_sse_daily_sina", "Get SSE option daily K-line", ["symbol"]],
  ["option_commodity_hist", "Get commodity option history (DCE/SHFE/CZCE)", ["symbol", "exchange", "trade_date"]],
  ["futures_zh_hist", "Get futures historical market data", ["symbol", "period", "source"]],
  ["match_main_contract", "Get main futures contracts by exchange symbol", ["symbol", "exchange"]],
  ["futures_basis", "Get futures basis and spot structure data", ["mode", "date", "symbol"]],
  ["fund_meta", "Get fund metadata and purchase status", ["mode"]],
  ["fund_etf_market", "Get ETF market data", ["mode", "symbol", "period", "start_date", "end_date", "adjust"]],
  ["fund_open_info", "Get open fund NAV and indicator data", ["symbol", "indicator"]],
  ["macro_china_all", "Get merged China macroeconomic datasets", ["datasets"]],
  ["commodity_basis", "Get commodity spot and basis data", ["mode", "symbol", "date"]],
  ["spot_sge", "Get Shanghai Gold Exchange data", ["mode", "symbol"]],
  ["bond_zh_hs_market", "Get Shanghai and Shenzhen bond market data", ["mode", "symbol"]],
  ["bond_zh_hs_cov_market", "Get Shanghai and Shenzhen convertible bond data", ["mode", "symbol"]],
  ["bond_cb_meta", "Get convertible bond metadata", ["mode", "symbol"]],
  ["stock_board_industry", "Get industry board list or historical data", ["mode", "symbol", "start_date", "end_date", "period", "adjust"]],
  ["stock_board_concept", "Get concept board list or historical data", ["mode", "symbol", "start_date", "end_date", "period", "adjust"]],
].map(([name, description, params]) => ({ name, description, params }));

/**
 * Create a unified wrapper suitable for agent tool registration.
 *
 * @param {ConstructorParameters<typeof createClient>[0]} [options] Node client options.
 * @returns {{
 *   client: AkshareNodeClient,
 *   listTools: () => ToolDefinition[],
 *   call: (name: string, params?: Record<string, any>) => Promise<any>
 * }} Tool facade instance.
 */
export function createAkshareTool(options = {}) {
  const client = createClient(options);

  return {
    client,
    listTools() {
      return TOOL_DEFINITIONS.map((item) => ({ ...item, params: [...item.params] }));
    },
    async call(name, params = {}) {
      if (typeof client[name] !== "function") {
        throw new Error(`Unsupported tool: ${name}`);
      }
      return client[name](params);
    },
  };
}

export { TOOL_DEFINITIONS };
