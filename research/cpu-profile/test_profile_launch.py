import platform,shutil,subprocess,tempfile,unittest
from pathlib import Path
from wine_profile_launch import wrapper_command

@unittest.skipUnless(platform.system()=='Darwin' and shutil.which('clang'),'macOS clang required')
class LaunchTests(unittest.TestCase):
    def test_preload_reaches_native_child_through_original_shell_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=Path(tmp);lib=h/'probe library.dylib';probe=h/'native probe';wrapper=h/'original wrapper.sh'
            (h/'lib.c').write_text('int profiler_marker(void){return 42;}\n')
            (h/'probe.c').write_text('#include <dlfcn.h>\nint main(void){int (*f)(void)=dlsym(RTLD_DEFAULT,"profiler_marker");return f&&f()==42?0:1;}\n')
            subprocess.run(['clang','-dynamiclib',str(h/'lib.c'),'-o',str(lib)],check=True,capture_output=True)
            subprocess.run(['clang',str(h/'probe.c'),'-o',str(probe)],check=True,capture_output=True)
            wrapper.write_text('#!/bin/bash\nset -euo pipefail\nprintf "%s\\n" "$0"\nexec "$1"\n')
            original=wrapper.read_bytes()
            result=subprocess.run(wrapper_command(wrapper,lib,str(probe)),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),str(wrapper))
            self.assertEqual(wrapper.read_bytes(),original)

if __name__=='__main__':unittest.main()
