import { INTERFACE_GROUPS, createTypedClient } from "./index.js";
import { TOOL_DEFINITIONS } from "./tool.js";

const TOOL_MAP = new Map(TOOL_DEFINITIONS.map((item) => [item.name, item]));

/**
 * Build grouped tool registries for agent integration.
 *
 * @param {ConstructorParameters<typeof createTypedClient>[0]} [options] Client options.
 * @returns {{
 *   groups: Record<string, Array<{ name: string, description: string, params: string[] }>>,
 *   handlers: Record<string, Record<string, (params?: Record<string, any>) => Promise<any>>>,
 *   getGroup: (groupName: string) => Array<{ name: string, description: string, params: string[] }>,
 *   getTool: (toolName: string) => { name: string, description: string, params: string[], group: string } | null,
 *   invoke: (toolName: string, params?: Record<string, any>) => Promise<any>
 * }} Agent tool registry.
 */
export function createAgentToolRegistry(options = {}) {
  const typedClient = createTypedClient(options);

  const groups = Object.fromEntries(
    Object.entries(INTERFACE_GROUPS).map(([groupName, methodNames]) => [
      groupName,
      methodNames.map((methodName) => ({ ...TOOL_MAP.get(methodName) })),
    ]),
  );

  const handlers = Object.fromEntries(
    Object.entries(INTERFACE_GROUPS).map(([groupName, methodNames]) => [
      groupName,
      Object.fromEntries(
        methodNames.map((methodName) => [methodName, typedClient[groupName][methodName]]),
      ),
    ]),
  );

  return {
    groups,
    handlers,
    getGroup(groupName) {
      return groups[groupName] ? groups[groupName].map((item) => ({ ...item, params: [...item.params] })) : [];
    },
    getTool(toolName) {
      const definition = TOOL_MAP.get(toolName);
      if (!definition) {
        return null;
      }
      const group = Object.entries(INTERFACE_GROUPS).find(([, names]) => names.includes(toolName))?.[0] || null;
      return group ? { ...definition, params: [...definition.params], group } : null;
    },
    async invoke(toolName, params = {}) {
      const tool = this.getTool(toolName);
      if (!tool) {
        throw new Error(`Unsupported tool: ${toolName}`);
      }
      return handlers[tool.group][toolName](params);
    },
  };
}

