import os
import subprocess
from pathlib import Path
import importlib.resources
from SCons.Script import Builder

def get_resource_path(package_subfolder, filename):
    """Finds a packaged resource (like templates or i18n files)."""
    # If the file exists locally, use the local file
    if os.path.exists(filename):
        return os.path.abspath(filename)
    
    # Try finding it in the package resources
    try:
        ref = importlib.resources.files(f"cv_cli.{package_subfolder}") / filename
        if ref.exists():
            return str(ref)
    except Exception as e:
        print(f"Error finding resource {filename} in packaged {package_subfolder}: {e}")
    
    return filename

def combine_yaml_files(content_file, i18n_file, output_file):
    """ Combine content YAML with i18n YAML """
    try:
        with open(output_file, 'w', encoding='utf-8') as outf:
            # First, write the content file
            with open(content_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
            outf.write('\n') # Ensure newline between files
            # Then, append the i18n file
            with open(i18n_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
        return True
    except Exception as e:
        print(f"Error combining YAML files: {e}")
        return False

def tex_from_yaml(target, source, env):
    """ Build LaTeX from YAML using pandoc """
    template = env.get('CV_TEMPLATE', 'template-cv.tex')
    template_path = get_resource_path('templates', template)
    
    try:
        subprocess.run(
            args=[
                'pandoc',
                f'--metadata-file={Path(str(source[0]))}',
                f'--template={Path(template_path)}',
                f'-o', str(Path(str(target[0])))
            ], 
            input='', text=True, check=True, capture_output=True
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Pandoc failed: {e}")
        if e.stderr: print(f"Error output: {e.stderr}")
        if e.stdout: print(f"Output: {e.stdout}")
        return 1

def pdf_from_tex(target, source, env):
    """ Build PDF from LaTeX using pdflatex """
    build_path = Path(str(target[0])).parent.absolute()
    tex_file = Path(str(source[0]))
    tex_filename = tex_file.name
    
    try:
        print(f"Building PDF from {tex_filename} in {build_path}")
        
        # First pass
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)

        # Second pass for cross-references
        result = subprocess.run(
            args=['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)
        
        # Check if PDF was actually created
        pdf_path = build_path / f"{tex_file.stem}.pdf"
        if pdf_path.exists(): 
            print(f"Successfully generated {pdf_path}")
            return 0
        else:
            print(f"PDF file was not created: {pdf_path}")
            return 1
        
    except subprocess.CalledProcessError as e:
        print(f"pdflatex failed: {e}")
        if e.stdout: print(f"stdout: {e.stdout}")
        if e.stderr: print(f"stderr: {e.stderr}")
        
        log_file = build_path / f"{tex_file.stem}.log"
        if log_file.exists():
            print(f"\nLast 20 lines of {log_file}:")
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        return 1

def setup_cv_env(env):
    """Appends CV compilation builders to the SCons environment."""
    env.Append(BUILDERS={
        'BuildTex': Builder(action=tex_from_yaml, suffix='.tex', src_suffix='.yaml'),
        'BuildPdf': Builder(action=pdf_from_tex, suffix='.pdf', src_suffix='.tex')
    })
