"""
Package Manager - Auto-install missing Python packages safely

Whitelist approach: Only allows known-safe packages for data science.
"""
import subprocess
import sys
from typing import List, Optional
import asyncio


class PackageManager:
    """Safe package installation manager."""
    
    # Whitelist of allowed packages (data science & visualization only)
    ALLOWED_PACKAGES = {
        # Data processing
        'pandas', 'numpy', 'scipy', 'openpyxl', 'xlrd', 'pyarrow',
        
        # Visualization
        'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair',
        
        # Machine learning (basic)
        'scikit-learn', 'statsmodels',
        
        # Utilities
        'tabulate', 'tqdm', 'colorama'
    }
    
    def __init__(self):
        self.installed_cache = set()
    
    def is_package_allowed(self, package_name: str) -> bool:
        """Check if package is in whitelist."""
        return package_name.lower() in self.ALLOWED_PACKAGES
    
    async def ensure_package(
        self,
        package_name: str,
        job_id: Optional[str] = None
    ) -> bool:
        """
        Ensure package is installed, install if missing and allowed.
        
        Args:
            package_name: Name of package to check/install
            job_id: Optional job ID for logging
            
        Returns:
            True if package available, False otherwise
        """
        # Check if already installed
        try:
            __import__(package_name)
            return True
        except ImportError:
            pass
        
        # Check if in cache (already tried installing)
        if package_name in self.installed_cache:
            return True
        
        # Check whitelist
        if not self.is_package_allowed(package_name):
            if job_id:
                from core.events import events
                await events.log(
                    job_id,
                    f"⚠️ Package '{package_name}' not in whitelist. Cannot auto-install.",
                    "warning"
                )
            return False
        
        # Install package
        if job_id:
            from core.events import events
            await events.log(job_id, f"📦 Installing {package_name}...", "info")
        
        try:
            # Install using pip
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.installed_cache.add(package_name)
                if job_id:
                    await events.log(job_id, f"✅ Installed {package_name}", "success")
                return True
            else:
                if job_id:
                    await events.log(
                        job_id,
                        f"❌ Failed to install {package_name}: {stderr.decode()[:100]}",
                        "error"
                    )
                return False
                
        except Exception as e:
            if job_id:
                from core.events import events
                await events.log(
                    job_id,
                    f"❌ Error installing {package_name}: {str(e)}",
                    "error"
                )
            return False
    
    async def ensure_packages(
        self,
        package_names: List[str],
        job_id: Optional[str] = None
    ) -> bool:
        """
        Ensure multiple packages are installed.
        
        Returns:
            True if all packages available, False otherwise
        """
        results = []
        for package in package_names:
            result = await self.ensure_package(package, job_id)
            results.append(result)
        
        return all(results)


# Global instance
package_manager = PackageManager()
