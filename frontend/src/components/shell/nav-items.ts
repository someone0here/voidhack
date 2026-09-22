export interface NavTabItem {
  id: string;
  pathSegment: string;
  label: string;
  badge: string;
  icon: string;
  classification: string;
}

export const NAV_TABS: NavTabItem[] = [
  {
    id: 'intake',
    pathSegment: 'intake',
    label: 'Evidence Intake',
    badge: '01',
    icon: '📥',
    classification: 'ARTIFACTS // PARSING',
  },
  {
    id: 'correlation',
    pathSegment: 'correlation',
    label: 'Correlation Board',
    badge: '02',
    icon: '🕸',
    classification: 'NETWORK // LINKAGE',
  },
  {
    id: 'risk',
    pathSegment: 'risk',
    label: 'Risk Desk',
    badge: '03',
    icon: '⚖',
    classification: 'HEURISTICS // SCORING',
  },
  {
    id: 'brief',
    pathSegment: 'brief',
    label: 'Investigative Brief',
    badge: '04',
    icon: '📄',
    classification: 'SEC 63 BSA // COURT READY',
  },
];
