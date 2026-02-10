import React from 'react';
import packageJson from '../../../package.json';

// Get build info from environment variables (set during build)
const buildInfo = {
  version: packageJson.version,
  gitSha: process.env.REACT_APP_GIT_SHA || 'dev',
  buildTime: process.env.REACT_APP_BUILD_TIME || '',
};

const Footer: React.FC = () => {
  const formatBuildTime = (time: string) => {
    if (!time) return 'Development';
    try {
      const date = new Date(time);
      return date.toLocaleString('pl-PL', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return time;
    }
  };

  // Short SHA (first 7 characters)
  const shortSha = buildInfo.gitSha.substring(0, 7);

  return (
    <footer
      role="contentinfo"
      className="mt-auto py-3 px-6 border-t border-gray-200 bg-white text-xs text-gray-500"
    >
      <div className="flex items-center justify-between">
        {/* Left side - Copyright */}
        <div>
          © {new Date().getFullYear()} Speecher. All rights reserved.
        </div>

        {/* Right side - Version info */}
        <div className="flex items-center space-x-3">
          <span className="hidden sm:inline">
            Version:{' '}
            <span className="font-mono font-medium text-gray-700">
              {buildInfo.version}
            </span>
          </span>

          {buildInfo.gitSha && (
            <span className="hidden md:inline">
              SHA:{' '}
            <span className="font-mono font-medium text-gray-700">
                {shortSha}
              </span>
            </span>
          )}

          <span className="hidden lg:inline">
            Build:{' '}
            <span className="font-medium text-gray-700">
              {formatBuildTime(buildInfo.buildTime)}
            </span>
          </span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
