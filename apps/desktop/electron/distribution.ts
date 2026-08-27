import fs from 'node:fs'
import path from 'node:path'

interface DistributionRepository {
  slug: string
  web: string
  https: string
  ssh: string
  raw_base: string
  archive_base: string
}

interface DistributionUpdate {
  branch: string
  allow_upstream_sync: boolean
}

interface DistributionMetadata {
  id: string
  display_name: string
  version: string
  repository: DistributionRepository
  update: DistributionUpdate
}

function distributionCandidates(): string[] {
  return [
    path.join(process.resourcesPath || '', 'distribution', 'distribution.json'),
    path.resolve(__dirname, '../../..', 'downstream', 'distribution.json'),
    path.resolve(process.cwd(), '../../downstream/distribution.json')
  ]
}

function loadDistributionMetadata(metadataPath?: string): DistributionMetadata {
  const candidate = metadataPath || distributionCandidates().find(item => fs.existsSync(item))

  if (!candidate) {
    throw new Error('downstream/distribution.json is required for Desktop bootstrap')
  }

  return JSON.parse(fs.readFileSync(candidate, 'utf8')) as DistributionMetadata
}

function distributionRawUrl(ref: string, scriptName: string): string {
  const repository = loadDistributionMetadata().repository
  const encodedRef = ref.split('/').map(encodeURIComponent).join('/')

  return `${repository.raw_base}/${encodedRef}/scripts/${encodeURIComponent(scriptName)}`
}

function distributionInstallArgs(): string[] {
  const repository = loadDistributionMetadata().repository

  return [
    '-RepositoryUrlHttps',
    repository.https,
    '-RepositoryUrlSsh',
    repository.ssh,
    '-RepositoryArchiveBase',
    repository.archive_base
  ]
}

export { distributionInstallArgs, distributionRawUrl, loadDistributionMetadata }
export type { DistributionMetadata }
