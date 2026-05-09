const fs = require('fs');
const path = require('path');

const REQUIRED_DIMENSIONS = [
  'repository_identity',
  'license',
  'maintenance_health',
  'install_postinstall_risk',
  'dependency_risk',
  'docker_ci_script_risk',
  'runtime_permissions',
  'browser_profile_handling',
  'credential_handling',
  'network_behavior',
  'prompt_injection_data_exfiltration',
  'windows_operational_risk',
  'project_fit',
];

function asText(value) {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value);
}

function daysSince(dateText) {
  if (!dateText) {
    return null;
  }
  const parsed = Date.parse(dateText);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return Math.floor((Date.now() - parsed) / (1000 * 60 * 60 * 24));
}

function dim(rating, rationale, evidence = []) {
  return { rating, rationale, evidence };
}

function maxRisk(ratings) {
  if (ratings.includes('high')) {
    return 'high';
  }
  if (ratings.includes('medium')) {
    return 'medium';
  }
  if (ratings.every((rating) => rating === 'low')) {
    return 'low';
  }
  return 'unknown';
}

function reviewLocal(evidence) {
  const name = evidence.candidate_name;
  const isFts = name.includes('FTS5');
  const isPattern = name.includes('Karpathy');
  const fit = isFts || isPattern || name.includes('Project-owned') || name.includes('Obsidian-compatible')
    ? 'high'
    : 'medium';
  const disposition = isPattern ? 'approve_pattern_only' : 'approve_initial_component';
  const dimensions = {
    repository_identity: dim('low', 'Local architecture/component or documented method; no third-party runtime dependency is needed.', evidence.source_urls),
    license: dim('low', 'No external code license is incorporated for the repo-owned implementation; public docs are used as references only.'),
    maintenance_health: dim('low', 'The implementation surface is owned by this project and can be validated with local scripts.'),
    install_postinstall_risk: dim('low', 'No install or lifecycle scripts are required for this candidate.'),
    dependency_risk: dim('low', isFts ? 'Uses SQLite FTS5 already available in the local SQLite build.' : 'Uses Markdown/SQLite conventions rather than a new package stack.'),
    docker_ci_script_risk: dim('low', 'No Docker, CI, or shell script execution is required.'),
    runtime_permissions: dim('low', 'Runtime scope is limited to this workspace, generated Markdown, and SQLite.'),
    browser_profile_handling: dim('low', 'No browser, cookies, or profile access is required.'),
    credential_handling: dim('low', 'No credentials are required for the initial local implementation.'),
    network_behavior: dim('low', 'No network access is required for local generation/search after source data is in SQLite.'),
    prompt_injection_data_exfiltration: dim('medium', 'Generated synthesis still needs source-citation and prompt-injection-aware validation because source content can contain instructions.'),
    windows_operational_risk: dim('low', 'Plain files and SQLite have low Windows operational risk.'),
    project_fit: dim(fit, 'Directly matches the WhatsApp-to-SQLite-to-Markdown KB use case.'),
  };
  return {
    candidate_name: name,
    overall_risk: maxRisk(Object.values(dimensions).map((item) => item.rating).filter((rating) => rating !== 'high')),
    fit_rating: fit,
    final_disposition: disposition,
    summary: `${name} remains suitable for the initial KB path because it avoids external code execution and keeps SQLite provenance central.`,
    dimensions,
    recommendation_changes_goal005: false,
  };
}

function reviewExternal(evidence) {
  const name = evidence.candidate_name;
  const github = evidence.github || {};
  const metadata = github.metadata || {};
  const analysis = github.static_analysis || {};
  const mentions = analysis.mentions || {};
  const packageSummaries = analysis.package_summaries || [];
  const lifecycleScripts = packageSummaries.flatMap((pkg) => Object.keys(pkg.lifecycle_scripts || {}));
  const depCount = packageSummaries.reduce((sum, pkg) => sum + (pkg.dependencies_count || 0) + (pkg.dev_dependencies_count || 0) + (pkg.optional_dependencies_count || 0), 0);
  const pushedDays = daysSince(metadata.pushed_at);
  const licenseKey = metadata.license && metadata.license.key ? metadata.license.key : null;
  const files = analysis.file_paths || [];
  const dockerFiles = analysis.docker_files || [];
  const ci = analysis.ci_workflows || [];
  const installScripts = analysis.install_scripts || [];
  const repoOk = Boolean(github.repo_api && github.repo_api.ok);

  let fit = 'medium';
  let disposition = 'defer_inspiration_only';
  if (name.includes('Cognee') || name.includes('CocoIndex')) {
    fit = 'medium';
    disposition = 'defer_later_optional_backend';
  }
  if (name.includes('OpenWolf') || name.includes('Obsidian Skills')) {
    fit = 'low';
    disposition = 'not_initial_dependency';
  }
  if (name.includes('LLM Wiki desktop') || name.includes('claude-obsidian') || name.includes('Ars Contexta') || name.includes('Pal')) {
    fit = 'medium';
    disposition = 'defer_compare_or_inspiration_only';
  }

  const dependencyRisk = depCount > 120 ? 'high' : depCount > 0 || files.some((file) => /lock|requirements|pyproject|package\.json/i.test(file)) ? 'medium' : 'unknown';
  const runtimeRisk = mentions.browser_or_profile || mentions.network_or_cloud || mentions.llm_agent_surface ? 'medium' : 'unknown';
  const networkRisk = mentions.network_or_cloud ? 'medium' : 'unknown';
  const windowsRisk = mentions.unix_shell_or_docker || dockerFiles.length || installScripts.length ? 'medium' : 'unknown';
  const licenseRisk = licenseKey === 'gpl-3.0' || licenseKey === 'agpl-3.0' ? 'high' : licenseKey ? 'medium' : 'unknown';
  const maintenanceRisk = metadata.archived ? 'high' : pushedDays === null ? 'unknown' : pushedDays > 365 ? 'medium' : 'low';
  const installRisk = lifecycleScripts.length || installScripts.length || dockerFiles.length ? 'medium' : 'unknown';

  const dimensions = {
    repository_identity: dim(repoOk ? 'low' : 'unknown', repoOk ? `Primary repository resolved as ${metadata.full_name || github.repo}.` : 'Repository identity could not be fully verified from public metadata.', evidence.source_urls),
    license: dim(licenseRisk, licenseKey ? `GitHub reports license ${licenseKey}. Compatibility must be checked before adoption.` : 'License evidence missing or unavailable.'),
    maintenance_health: dim(maintenanceRisk, pushedDays === null ? 'Latest push/release evidence unavailable.' : `Latest pushed_at is ${metadata.pushed_at} (${pushedDays} days before review runtime).`),
    install_postinstall_risk: dim(installRisk, lifecycleScripts.length ? `Lifecycle scripts found: ${lifecycleScripts.join(', ')}.` : dockerFiles.length || installScripts.length ? 'Install scripts or Docker surfaces are present.' : 'No candidate execution was performed; install risk remains unknown without isolated test.'),
    dependency_risk: dim(dependencyRisk, depCount ? `Package manifests expose about ${depCount} direct/dev/optional dependencies across inspected package.json files.` : 'No package dependency count was available from inspected static files.'),
    docker_ci_script_risk: dim(dockerFiles.length || ci.length || installScripts.length ? 'medium' : 'unknown', `Static files found Docker=${dockerFiles.length}, CI workflows=${ci.length}, install scripts=${installScripts.length}.`),
    runtime_permissions: dim(runtimeRisk, mentions.llm_agent_surface ? 'Evidence mentions LLM/agent/MCP/tooling behavior that may need broad workspace access.' : 'Runtime permission surface is unclear from bounded static evidence.'),
    browser_profile_handling: dim(mentions.browser_or_profile ? 'medium' : 'low', mentions.browser_or_profile ? 'Evidence mentions browser/profile/extension/cookie-related behavior; must be isolated from personal profiles.' : 'No browser/profile handling found in inspected evidence.'),
    credential_handling: dim(mentions.credentials_or_env ? 'medium' : 'unknown', mentions.credentials_or_env ? 'Evidence mentions API keys, tokens, secrets, or env files.' : 'Credential behavior not clearly documented in inspected evidence.'),
    network_behavior: dim(networkRisk, mentions.network_or_cloud ? 'Evidence mentions API/cloud/server/MCP/web behavior.' : 'Network behavior is not clearly documented.'),
    prompt_injection_data_exfiltration: dim('medium', 'Any external LLM/agent/KB tool that ingests WhatsApp-derived content must be treated as prompt-injection and data-exfiltration sensitive until isolated execution tests prove otherwise.'),
    windows_operational_risk: dim(windowsRisk, windowsRisk === 'medium' ? 'Docker, shell, native, or Unix-oriented surfaces may complicate Windows operation.' : 'Windows operation is unknown from bounded static evidence.'),
    project_fit: dim(fit, fit === 'low' ? 'The project is not a direct initial fit for WhatsApp-to-SQLite-to-Markdown generation.' : 'Potentially useful as later inspiration or optional component, but broader than the first local KB baseline.'),
  };

  return {
    candidate_name: name,
    overall_risk: maxRisk(Object.values(dimensions).map((item) => item.rating)),
    fit_rating: fit,
    final_disposition: disposition,
    summary: `${name} should not become an initial implementation dependency. Static evidence suggests useful ideas, but unresolved install/runtime/dependency surfaces remain broader than the repo-owned Markdown baseline.`,
    dimensions,
    recommendation_changes_goal005: false,
  };
}

function buildReview(evidence) {
  const kind = evidence.kind || '';
  const review = kind.startsWith('local') || kind === 'method_pattern' || kind === 'markdown_format'
    ? reviewLocal(evidence)
    : reviewExternal(evidence);
  review.required_dimensions_present = REQUIRED_DIMENSIONS.every((name) => review.dimensions[name]);
  review.source_urls = evidence.source_urls || [];
  review.reviewed_at = new Date().toISOString();
  review.reviewer_method = 'promptfoo-custom-js-static-provider';
  return review;
}

module.exports = class KbSafetyProvider {
  id() {
    return 'kb-safety-static-reviewer';
  }

  async callApi(prompt, context) {
    const vars = (context && context.vars) || {};
    const evidence = typeof vars.candidate_json === 'string'
      ? JSON.parse(vars.candidate_json)
      : vars.candidate_json;
    const review = buildReview(evidence);
    if (vars.review_output_path) {
      const outputPath = path.resolve(process.cwd(), vars.review_output_path);
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
      fs.writeFileSync(outputPath, `${JSON.stringify(review, null, 2)}\n`, 'utf8');
    }
    return {
      output: JSON.stringify(review, null, 2),
      metadata: {
        candidate_name: evidence.candidate_name,
        dimensions: REQUIRED_DIMENSIONS.length,
      },
    };
  }
};
