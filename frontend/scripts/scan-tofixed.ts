// frontend/scripts/scan-tofixed.ts
/**
 * Automated scanner to detect and fix unsafe .toFixed() calls
 * Run:
 *   npx tsx frontend/scripts/scan-tofixed.ts --root ./frontend --fix
 * Flags:
 *   --root <dir>    Root to scan (default: ./frontend)
 *   --ext <list>    Extensions comma-separated (default: ts,tsx,js,jsx)
 *   --fix           Apply fixes in-place (default: dry-run report only)
 *   --dry           Force dry-run even if --fix passed
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { glob } from 'glob';

interface ToFixedIssue {
  file: string;
  line: number;
  column: number;
  code: string;
  suggestion: string;
}

type IssueMap = Record<string, ToFixedIssue[]>;

export class ToFixedScanner {
  private issues: ToFixedIssue[] = [];

  // Regex patterns to detect .toFixed() calls (kept simple, line-based)
  private patterns = {
    direct: /([A-Za-z_$][\w$]*)\.toFixed\((\d+)\)/g,                // value.toFixed(n)
    expression: /\(([^)]+?)\)\.toFixed\((\d+)\)/g,                  // (expr).toFixed(n)
    property: /([A-Za-z_$][\w$]*\.[A-Za-z_$][\w$]*)\.toFixed\((\d+)\)/g, // obj.prop.toFixed(n)
    array: /([A-Za-z_$][\w$]*\[[^\]]+\])\.toFixed\((\d+)\)/g,       // arr[i].toFixed(n)
  };

  async scanDirectory(root: string, exts: string[]): Promise<void> {
    const cwd = path.resolve(root);
    const pattern = `**/*.{${exts.join(',')}}`;
    const ignore = ['**/node_modules/**','**/dist/**','**/.next/**','**/build/**','**/out/**'];
  
    const files = await glob(pattern, { cwd, absolute: true, nodir: true, ignore });
  
    // debug
    if (process.argv.includes('--debug')) {
      console.log({ cwd, pattern, matched: files.length, sample: files.slice(0, 10) });
    }
  
    if (files.length === 0) {
      console.warn(`⚠️  No files matched pattern under: ${cwd}`);
      return;
    }
    for (const f of files) await this.scanFile(f);
  }

  private async scanFile(filePath: string): Promise<void> {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.split('\n');

      // Track lastIndex resets for each new line to avoid sticky matches carrying over
      const resetPatterns = () => {
        for (const p of Object.values(this.patterns)) p.lastIndex = 0;
      };

      lines.forEach((line, idx) => {
        const trimmed = line.trim();
        // Skip obvious non-code lines (fast path)
        if (
          trimmed.startsWith('//') ||
          trimmed.startsWith('*') ||
          trimmed.startsWith('/*') ||
          trimmed.startsWith('@') ||
          trimmed.startsWith('import ')
        ) {
          return;
        }

        resetPatterns();
        for (const [patternName, pattern] of Object.entries(this.patterns)) {
          let match: RegExpExecArray | null;
          while ((match = pattern.exec(line)) !== null) {
            const column = match.index;
            const code = match[0];
            // Heuristic: first capture group tends to be the “value”
            const variable = match[1] ?? 'value';
            const decimals = match[2] ?? '2';

            this.issues.push({
              file: filePath,
              line: idx + 1,
              column,
              code,
              suggestion: this.generateSuggestion(code, variable, decimals),
            });
          }
        }
      });
    } catch (err) {
      console.error(`❌ Failed to read ${filePath}:`, (err as Error).message);
    }
  }

  private generateSuggestion(code: string, variable: string, decimals: string): string {
    const expr = (variable ?? 'value').trim();
  
    // If someone wrote (x*100).toFixed(n) and we want fraction input for percentages,
    // remove "*100" to pass the base fraction to safePercentage()
    const fractionExpr = expr
      .replace(/\s+/g, '')
      .replace(/^\((.+)\*100\)$/, '$1')
      .replace(/^(.+)\*100$/, '$1');
  
    // TIME: keep ms (safeTime will convert ms->s or auto-scale)
    if (/time|ms/i.test(code)) {
      // use auto here if you prefer dynamic scaling:
      // return `safeTime(${expr}, { unit: 'auto' })`;
      return `safeTime(${expr})`;
    }
  
    // CURRENCY: use Intl-based function with defaults
    if (/\bcost\b|\bprice\b|\$/i.test(code)) {
      // If you want USD enforced: safeCurrency(${expr}, { currency: 'USD' })
      return `safeCurrency(${expr})`;
    }
  
    // PERCENTAGE: prefer fraction inputs (expectsFraction: true by default)
    if (/\bconfidence\b|\bscore\b|%/i.test(code)) {
      return `safePercentage(${fractionExpr})`;
    }
  
    // DEFAULT: keep the detected decimals
    return `safeToFixed(${expr}, ${decimals})`;
  }

  private groupIssues(): IssueMap {
    return this.issues.reduce((acc, issue) => {
      (acc[issue.file] ??= []).push(issue);
      return acc;
    }, {} as IssueMap);
  }

  async generateReport(): Promise<string> {
    const byFile = this.groupIssues();
    const report: string[] = [];

    report.push('# toFixed() Safety Scan Report');
    report.push(`Found ${this.issues.length} potential issue(s)\n`);

    for (const [file, issues] of Object.entries(byFile)) {
      report.push(`\n## ${path.relative(process.cwd(), file)}`);
      report.push(`Issues found: ${issues.length}\n`);
      for (const issue of issues) {
        report.push(`**Line ${issue.line}:** \`${issue.code}\``);
        report.push(`Suggestion: \`${issue.suggestion}\``);
        report.push('');
      }
    }

    report.push('\n## Notes');
    report.push('- Ensure `@/lib/safe-formatters` exports: `safeToFixed`, `safeCurrency`, `safePercentage`, `safeTime`.');
    report.push('- Scanner is heuristic; please review each suggested change.');

    return report.join('\n');
  }

  async applyFixes(dryRun = true): Promise<void> {
    const byFile = this.groupIssues();

    for (const [file, issues] of Object.entries(byFile)) {
      const content = await fs.readFile(file, 'utf-8');
      let modified = content;

      // Sort by position bottom-up to keep offsets stable
      const sorted = issues
        .map((iss) => ({ ...iss, pos: this.positionFromLine(modified, iss.line, iss.column) }))
        .sort((a, b) => b.pos - a.pos);

      for (const issue of sorted) {
        const lines = modified.split('\n');
        const line = lines[issue.line - 1] ?? '';
        // Replace only the first matching occurrence at/after column index
        const before = line.slice(0, issue.column);
        const after = line.slice(issue.column);
        const replacedAfter = after.replace(issue.code, issue.suggestion);
        if (after !== replacedAfter) {
          lines[issue.line - 1] = before + replacedAfter;
          modified = lines.join('\n');
        }
      }

      // Add import if any replacement occurred and import not present
      if (modified !== content && !/from ['"]@\/lib\/safe-formatters['"]/.test(modified)) {
        const importLine = `import { safeToFixed, safeCurrency, safePercentage, safeTime } from '@/lib/safe-formatters';\n`;
        const firstImportMatch = modified.match(/^import .*;$/m);
        if (firstImportMatch && firstImportMatch.index !== undefined) {
          const idx = firstImportMatch.index;
          modified = modified.slice(0, idx) + importLine + modified.slice(idx);
        } else {
          modified = importLine + '\n' + modified;
        }
      }

      if (dryRun) {
        console.log(`Would update ${path.relative(process.cwd(), file)} with ${issues.length} fix(es)`);
      } else if (modified !== content) {
        await fs.writeFile(file, modified, 'utf-8');
        console.log(`Updated ${path.relative(process.cwd(), file)} with ${issues.length} fix(es)`);
      }
    }
  }

  private positionFromLine(source: string, line: number, col: number): number {
    const lines = source.split('\n');
    let pos = 0;
    for (let i = 0; i < line - 1; i++) pos += lines[i].length + 1;
    return pos + col;
  }
}

/* ----------------------------- CLI Entrypoint ----------------------------- */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const args = process.argv.slice(2);
  const root = getFlag(args, '--root') ?? './frontend';
  const extList = (getFlag(args, '--ext') ?? 'ts,tsx,js,jsx').split(',').map(s => s.trim());
  const doFix = args.includes('--fix') && !args.includes('--dry');

  const scanner = new ToFixedScanner();

  console.log('🔍 Scanning for unsafe .toFixed() calls...\n');
  await scanner.scanDirectory(root, extList);

  const report = await scanner.generateReport();
  console.log(report);

  await fs.writeFile(path.resolve(process.cwd(), 'tofixed-scan-report.md'), report, 'utf-8');
  console.log('\n📄 Report saved to tofixed-scan-report.md');

  if (doFix) {
    console.log('\n✍️  Applying fixes…');
    await scanner.applyFixes(false);
    console.log('✅ Fixes applied!');
  } else {
    console.log('\n💡 Run with --fix to automatically apply fixes');
  }
}

function getFlag(argv: string[], name: string): string | undefined {
  const idx = argv.indexOf(name);
  if (idx === -1) return undefined;
  const val = argv[idx + 1];
  if (!val || val.startsWith('-')) return undefined;
  return val;
}

// ESM-safe "main" check
if (pathToFileURL(process.argv[1]).href === import.meta.url) {
  main().catch((err) => {
    console.error('❌ Scan failed:', err);
    process.exit(1);
  });
}
