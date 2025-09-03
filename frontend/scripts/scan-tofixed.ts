// frontend/scripts/scan-tofixed.ts
/**
 * Automated scanner to detect and fix unsafe .toFixed() calls
 * Run with: npx tsx scripts/scan-tofixed.ts
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { glob } from 'glob';

interface ToFixedIssue {
  file: string;
  line: number;
  column: number;
  code: string;
  suggestion: string;
}

export class ToFixedScanner {
  private issues: ToFixedIssue[] = [];
  
  // Regex patterns to detect .toFixed() calls
  private patterns = {
    // Direct .toFixed() calls: value.toFixed(n)
    direct: /(\w+)\.toFixed\((\d+)\)/g,
    
    // Chained calls: (value * 100).toFixed(n)
    expression: /\([^)]+\)\.toFixed\((\d+)\)/g,
    
    // Property access: obj.prop.toFixed(n)
    property: /(\w+\.\w+)\.toFixed\((\d+)\)/g,
    
    // Array access: arr[i].toFixed(n)
    array: /(\w+\[\w+\])\.toFixed\((\d+)\)/g,
  };

  async scanDirectory(dir: string): Promise<void> {
    const files = await glob(`${dir}/**/*.{ts,tsx,js,jsx}`, {
      ignore: ['**/node_modules/**', '**/dist/**', '**/.next/**'],
    });

    for (const file of files) {
      await this.scanFile(file);
    }
  }

  private async scanFile(filePath: string): Promise<void> {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      this.scanLine(filePath, line, index + 1);
    });
  }

  private scanLine(file: string, line: string, lineNumber: number): void {
    // Skip comments and imports
    if (line.trim().startsWith('//') || line.trim().startsWith('*') || line.includes('import')) {
      return;
    }

    for (const [patternName, pattern] of Object.entries(this.patterns)) {
      let match;
      while ((match = pattern.exec(line)) !== null) {
        const column = match.index;
        const code = match[0];
        const variable = match[1] || 'value';
        const decimals = match[2] || match[1];

        this.issues.push({
          file,
          line: lineNumber,
          column,
          code,
          suggestion: this.generateSuggestion(code, variable, decimals, patternName),
        });
      }
    }
  }

  private generateSuggestion(
    code: string, 
    variable: string, 
    decimals: string,
    patternType: string
  ): string {
    // Import statement to add
    const importStatement = `import { safeToFixed } from '@/lib/safe-formatters';`;

    // Based on the context, suggest appropriate formatter
    if (code.includes('cost') || code.includes('price') || code.includes('$')) {
      return `safeCurrency(${variable}, ${decimals})`;
    }
    
    if (code.includes('confidence') || code.includes('score') || code.includes('%')) {
      return `safePercentage(${variable})`;
    }
    
    if (code.includes('time') || code.includes('ms')) {
      return `safeTime(${variable})`;
    }

    // Default suggestion
    return `safeToFixed(${variable}, ${decimals})`;
  }

  async generateReport(): Promise<string> {
    const report = [];
    
    report.push('# toFixed() Safety Scan Report');
    report.push(`Found ${this.issues.length} potential issues\n`);

    // Group by file
    const byFile = this.issues.reduce((acc, issue) => {
      if (!acc[issue.file]) acc[issue.file] = [];
      acc[issue.file].push(issue);
      return acc;
    }, {} as Record<string, ToFixedIssue[]>);

    for (const [file, issues] of Object.entries(byFile)) {
      report.push(`\n## ${file}`);
      report.push(`Issues found: ${issues.length}\n`);

      for (const issue of issues) {
        report.push(`**Line ${issue.line}:** \`${issue.code}\``);
        report.push(`Suggestion: \`${issue.suggestion}\``);
        report.push('');
      }
    }

    // Generate fix script
    report.push('\n## Automated Fix Script');
    report.push('Run the following to automatically apply safe formatters:\n');
    report.push('```bash');
    report.push('npm install @/lib/safe-formatters');
    report.push('npx tsx scripts/apply-tofixed-fixes.ts');
    report.push('```');

    return report.join('\n');
  }

  async applyFixes(dryRun: boolean = true): Promise<void> {
    const byFile = this.issues.reduce((acc, issue) => {
      if (!acc[issue.file]) acc[issue.file] = [];
      acc[issue.file].push(issue);
      return acc;
    }, {} as Record<string, ToFixedIssue[]>);

    for (const [file, issues] of Object.entries(byFile)) {
      let content = await fs.readFile(file, 'utf-8');
      let modified = content;
      let needsImport = !content.includes('safe-formatters');

      // Apply fixes in reverse order to maintain line positions
      const sortedIssues = issues.sort((a, b) => b.line - a.line);

      for (const issue of sortedIssues) {
        const lines = modified.split('\n');
        const line = lines[issue.line - 1];
        const fixedLine = line.replace(issue.code, issue.suggestion);
        lines[issue.line - 1] = fixedLine;
        modified = lines.join('\n');
      }

      // Add import if needed
      if (needsImport && modified !== content) {
        const importLine = `import { safeToFixed, safeCurrency, safePercentage, safeTime } from '@/lib/safe-formatters';\n`;
        const firstImportIndex = modified.search(/^import/m);
        
        if (firstImportIndex !== -1) {
          modified = modified.slice(0, firstImportIndex) + importLine + modified.slice(firstImportIndex);
        } else {
          modified = importLine + '\n' + modified;
        }
      }

      if (dryRun) {
        console.log(`Would update ${file} with ${issues.length} fixes`);
      } else {
        await fs.writeFile(file, modified);
        console.log(`Updated ${file} with ${issues.length} fixes`);
      }
    }
  }
}

// CLI execution
if (require.main === module) {
  const scanner = new ToFixedScanner();
  
  (async () => {
    console.log('🔍 Scanning for unsafe .toFixed() calls...\n');
    
    await scanner.scanDirectory('./frontend');
    
    const report = await scanner.generateReport();
    console.log(report);
    
    // Save report
    await fs.writeFile('./tofixed-scan-report.md', report);
    console.log('\n📄 Report saved to tofixed-scan-report.md');
    
    // Ask about applying fixes
    if (process.argv.includes('--fix')) {
      await scanner.applyFixes(false);
      console.log('\n✅ Fixes applied!');
    } else {
      console.log('\n💡 Run with --fix flag to automatically apply fixes');
    }
  })();
}