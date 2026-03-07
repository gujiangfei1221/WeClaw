import cron from "node-cron";
import Database from "better-sqlite3";
import path from "node:path";
import type { ChatCompletionTool } from "openai/resources/chat/completions";
import { logger } from "../utils/logger.js";

// ==================== Cron 定时任务管理器（SQLite 持久化） ====================

interface CronJob {
  id: string;
  expression: string;
  description: string;
  userId: string;
  prompt: string; // AI 要执行的指令
  task: cron.ScheduledTask;
  createdAt: string;
}

/** 数据库行类型 */
interface CronJobRow {
  id: string;
  expression: string;
  description: string;
  user_id: string;
  prompt: string;
  created_at: string;
}

const jobs = new Map<string, CronJob>();
let nextId = 1;
let db: Database.Database | null = null;

// 用于存放外部回调，由 server.ts 注入
let onCronTrigger: ((userId: string, prompt: string) => Promise<void>) | null = null;

/**
 * 初始化 Cron 持久化数据库，并从中恢复已有任务
 *
 * 必须在 setCronTriggerCallback 之后调用（因为恢复任务时需要回调已注入）
 */
export function initCronDB(dbPath?: string): void {
  const resolvedPath = dbPath || path.resolve(process.env.DATA_DIR || "data", "memory.db");
  db = new Database(resolvedPath);

  // 建表（如果不存在）
  db.exec(`
    CREATE TABLE IF NOT EXISTS cron_jobs (
      id TEXT PRIMARY KEY,
      expression TEXT NOT NULL,
      description TEXT NOT NULL,
      user_id TEXT NOT NULL,
      prompt TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
  `);

  logger.info("Cron", `定时任务持久化表初始化完成`);

  // 从数据库恢复任务
  restoreJobs();
}

/**
 * 从数据库恢复所有定时任务（服务启动时调用）
 */
function restoreJobs(): void {
  if (!db) return;

  const rows = db.prepare("SELECT * FROM cron_jobs").all() as CronJobRow[];

  if (rows.length === 0) {
    logger.info("Cron", "数据库中无持久化任务");
    return;
  }

  for (const row of rows) {
    // 提取数字 ID，更新 nextId 避免冲突
    const numId = parseInt(row.id.replace("cron_", ""), 10);
    if (!isNaN(numId) && numId >= nextId) {
      nextId = numId + 1;
    }

    // 注册 node-cron 调度器
    const task = cron.schedule(row.expression, async () => {
      logger.info("Cron", `触发任务 ${row.id}: ${row.description}`);
      if (onCronTrigger) {
        try {
          await onCronTrigger(row.user_id, `[定时任务触发] ${row.description}\n请执行: ${row.prompt}`);
        } catch (err) {
          logger.error("Cron", `任务 ${row.id} 执行失败:`, err);
        }
      }
    });

    const job: CronJob = {
      id: row.id,
      expression: row.expression,
      description: row.description,
      userId: row.user_id,
      prompt: row.prompt,
      task,
      createdAt: row.created_at,
    };

    jobs.set(row.id, job);
    logger.info("Cron", `已恢复任务 ${row.id}: "${row.description}" (${row.expression})`);
  }

  logger.info("Cron", `共恢复 ${rows.length} 个定时任务`);
}

/**
 * 注册 Cron 触发时的回调函数
 */
export function setCronTriggerCallback(
  callback: (userId: string, prompt: string) => Promise<void>,
): void {
  onCronTrigger = callback;
}

/**
 * 添加一个定时任务（内存 + 数据库）
 */
export function addCronJob(
  userId: string,
  expression: string,
  description: string,
  prompt: string,
): string {
  // 验证 cron 表达式是否合法
  if (!cron.validate(expression)) {
    return `Cron 表达式无效: "${expression}"。正确格式示例: "0 9 * * *"（每天9点）, "*/5 * * * *"（每5分钟）`;
  }

  const id = `cron_${nextId++}`;
  const task = cron.schedule(expression, async () => {
    logger.info("Cron", `触发任务 ${id}: ${description}`);
    if (onCronTrigger) {
      try {
        await onCronTrigger(userId, `[定时任务触发] ${description}\n请执行: ${prompt}`);
      } catch (err) {
        logger.error("Cron", `任务 ${id} 执行失败:`, err);
      }
    }
  });

  const createdAt = new Date().toLocaleString("zh-CN");

  const job: CronJob = {
    id,
    expression,
    description,
    userId,
    prompt,
    task,
    createdAt,
  };

  jobs.set(id, job);

  // 持久化到数据库
  if (db) {
    try {
      db.prepare(
        "INSERT OR REPLACE INTO cron_jobs (id, expression, description, user_id, prompt, created_at) VALUES (?, ?, ?, ?, ?, ?)",
      ).run(id, expression, description, userId, prompt, createdAt);
    } catch (err) {
      logger.error("Cron", `持久化任务 ${id} 失败:`, err);
    }
  }

  logger.info("Cron", `已注册任务 ${id}: "${description}" (${expression})`);

  return `定时任务已创建:\n- ID: ${id}\n- 调度: ${expression}\n- 描述: ${description}\n- 执行内容: ${prompt}`;
}

/**
 * 列出用户的定时任务
 */
export function listCronJobs(userId: string): string {
  const userJobs = [...jobs.values()].filter((j) => j.userId === userId);
  if (userJobs.length === 0) return "当前没有活跃的定时任务。";

  return userJobs
    .map((j) => `- [${j.id}] ${j.description} | 调度: ${j.expression} | 创建: ${j.createdAt}`)
    .join("\n");
}

/**
 * 删除定时任务（内存 + 数据库）
 */
export function removeCronJob(jobId: string): string {
  const job = jobs.get(jobId);
  if (!job) return `未找到任务: ${jobId}`;

  job.task.stop();
  jobs.delete(jobId);

  // 从数据库删除
  if (db) {
    try {
      db.prepare("DELETE FROM cron_jobs WHERE id = ?").run(jobId);
    } catch (err) {
      logger.error("Cron", `从数据库删除任务 ${jobId} 失败:`, err);
    }
  }

  return `定时任务 ${jobId}（${job.description}）已删除`;
}

// ==================== Cron 工具定义（提供给大模型） ====================

export const cronToolDefinitions: ChatCompletionTool[] = [
  {
    type: "function",
    function: {
      name: "add_cron_job",
      description:
        "创建一个定时任务。任务会按照 cron 表达式的调度定期触发，届时 AI 会自动执行指定的操作并通过微信通知用户。常用 cron: '0 9 * * *'(每天9点), '0 */2 * * *'(每2小时), '30 8 * * 1-5'(工作日8:30)。",
      parameters: {
        type: "object",
        properties: {
          expression: {
            type: "string",
            description: "Cron 表达式，如 '0 9 * * *'",
          },
          description: {
            type: "string",
            description: "任务的简短描述，如 '每天早上提醒喝水'",
          },
          prompt: {
            type: "string",
            description: "定时触发时要 AI 执行的操作指令",
          },
        },
        required: ["expression", "description", "prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "list_cron_jobs",
      description: "列出当前所有活跃的定时任务",
      parameters: { type: "object", properties: {} },
    },
  },
  {
    type: "function",
    function: {
      name: "remove_cron_job",
      description: "删除一个定时任务",
      parameters: {
        type: "object",
        properties: {
          job_id: {
            type: "string",
            description: "要删除的任务 ID，如 'cron_1'",
          },
        },
        required: ["job_id"],
      },
    },
  },
];

/**
 * 执行 Cron 类工具
 */
export function executeCronTool(
  name: string,
  args: Record<string, any>,
  userId: string,
): string {
  switch (name) {
    case "add_cron_job":
      return addCronJob(userId, args.expression, args.description, args.prompt);
    case "list_cron_jobs":
      return listCronJobs(userId);
    case "remove_cron_job":
      return removeCronJob(args.job_id);
    default:
      return `未知 Cron 工具: ${name}`;
  }
}
