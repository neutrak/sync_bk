#!/usr/bin/env python3

#this backs up files (based on a manifest) into a .tar.gz file
#the .tar.gz can then be copied and un-packed to synchronize files

#we're gonna need some system calls for this
import sys
import os
import shutil
import subprocess

#general libraries
import tempfile
import time

#the manifest file is json
import json

#command-line arguments are handled with an option parser
import optparse

#the manifest name (within the backup archive)
MANIFEST_NAME='sync_manifest.json'
SYNC_SUBDIR='sync_bk'

def sync_cp_file(f,from_path,to_path):
	if(f['type']=='dir'):
		if(f['recurse']==True):
			#copy all files in the directory, etc.
			shutil.copytree(from_path+'/'+f['path'],to_path+'/'+f['path'])
		else:
			os.makedirs(to_path+'/'+f['path'])
			for filename in os.listdir(from_path+'/'+f['path']):
				if(not os.path.isdir(from_path+'/'+f['path']+'/'+filename)):
					shutil.copyfile(from_path+'/'+f['path']+'/'+filename,to_path+'/'+f['path']+'/'+filename)
	elif(f['type']=='file'):
		dir_ancestry=(f['path'].split('/'))
		directory='/'.join(dir_ancestry[0:len(dir_ancestry)-1])
		if(not os.path.exists(to_path+'/'+directory)):
			os.makedirs(to_path+'/'+directory)
		
		shutil.copyfile(from_path+'/'+f['path'],to_path+'/'+f['path'])
	else:
		print('Warn: Unrecognized file type for '+str(f)+'; skipping...')

#make a backup
def mk_bk(manifest,output_file,sync_dir):
	#if the manifest file doesn't exist, then exit now!
	if(not os.path.isfile(manifest)):
		print('Err: Manifest file could not be opened (probably missing!), exiting...')
		exit(1)
	
	#save the directory this script was run from
	#this is in case the given manifest was in a relative path
	run_dir=os.getcwd()
	
	#convert any relative paths into absolute paths
	if(not manifest.startswith('/')):
		manifest=run_dir+'/'+manifest
	if(not output_file.startswith('/')):
		output_file=run_dir+'/'+output_file
	
	fp=open(manifest,'r')
	fcontent=fp.read()
	fp.close()
	
	try:
		json_tree=json.loads(fcontent)
	except ValueError:
		json_tree=None
	
	if(json_tree is None):
		print('Err: Could not parse manifest file, exiting...')
		exit(1)
	
	for key in json_tree:
		print('json_tree['+str(key)+']='+str(json_tree[key]))
	
	start_path=json_tree['start_path']
	if(start_path is None):
		start_path=os_environ['HOME']
	
	sync_path=sync_dir+'/'+SYNC_SUBDIR
	os.mkdir(sync_path)
	
	for f in json_tree['files']:
		sync_cp_file(f,start_path,sync_path)
	
	os.chdir(sync_path+'/..')
	
#	manifest_basename=os.path.basename(manifest)
	
	#enforce naming convention for manifest post-copy
	#because we need to know what to look for when extracting
	manifest_basename=MANIFEST_NAME
	
	shutil.copyfile(manifest,sync_path+'/../'+manifest_basename)
	os.system('tar cvzf '+output_file+' '+manifest_basename+' '+SYNC_SUBDIR+'/')
	print('removing '+os.getcwd()+'/'+SYNC_SUBDIR+'/ '+manifest_basename)
	os.system('rm -rf '+SYNC_SUBDIR+'/ '+manifest_basename)

def resolve_bk(src,dest):
	got_opt=False
	
	while(not got_opt):
		print('Changes were found to the following file: '+dest)
		print('Would you like to keep the ')
		print("\t"+'[n]ewest')
		print("\t"+'[o]ldest')
		print("\t"+'[l]argest')
		print("\t"+'[s]mallest')
		print("\t"+'[a]rchive')
		print("\t"+'[f]ilesystem')
		print('or would you like to ')
		print("\t"+'view [d]iff')
		print("\t"+'[m]erge')
		print("?")
		
		option=(input().lower())[0]
		print('Got option '+str(option))
		
		#TODO: do what the option asked
		if(option=='n'):
			#keep newest
			got_opt=True
		elif(option=='o'):
			#keep oldest
			got_opt=True
		elif(option=='l'):
			#keep largest
			got_opt=True
		elif(option=='s'):
			#keep smallest
			got_opt=True
		elif(option=='a'):
			#keep archived copy (copy source to dest)
			got_opt=True
		elif(option=='f'):
			#keep filesystem copy (do nothing)
			got_opt=True
		elif(option=='d'):
			#view diff
			got_opt=True
		elif(option=='m'):
			#merge
			got_opt=True
		else:
			print('Unrecognized option, try again')
	
	#issue should now be resolved

#get all files (recursive os.listdir)
def full_file_list(start_path):
#	print('full_file_list debug; start_path='+start_path)
	
	acc=[]
	for f in os.listdir(start_path):
		fpath=start_path+'/'+f
		if(os.path.isdir(fpath)):
			acc.extend(full_file_list(fpath))
		else:
			acc.append(fpath)
	return acc

#synchronize from a backup
def sync_bk(sync_file,sync_dir):
	#save the directory this script was run from
	run_dir=os.getcwd()
	
	sync_path=sync_dir+'/'+SYNC_SUBDIR
	if(not os.path.exists(sync_path)):
		os.mkdir(sync_path)
	else:
		print('Warn: '+sync_path+' already existed; if this script was previously run without a clean exit you should delete this first')
		print('Delete? (y/n)')
		option=(input().lower())[0]
		print('Got option '+str(option))
		
		if(option=='y'):
			print('removing and re-making '+sync_path+'...')
			os.system('rm -rf '+sync_path)
			os.mkdir(sync_path)
	
	print(os.getcwd()+'$ tar xvzf -C \''+sync_path+'\' '+sync_file)
	os.system('tar -C \''+sync_path+'\' -xvzf '+sync_file)
	
	files=os.listdir(sync_path)
#	print('files (manifest+) are '+str(files))
	
	#after extracting, go to where the files were extracted
	os.chdir(sync_path)
	
	#if the manifest file doesn't exist, then exit now!
	if(not os.path.isfile(MANIFEST_NAME)):
		print('Err: Manifest file missing; this is NOT a valid archive; exiting...')
		exit(1)
	
	fp=open(MANIFEST_NAME,'r')
	fcontent=fp.read()
	fp.close()
	
	try:
		json_tree=json.loads(fcontent)
	except ValueError:
		print('Err: Could not parse manifest file, exiting...')
		exit(1)
	
	start_path=json_tree['start_path']
	if(start_path is None):
		start_path=os_environ['HOME']
	
	print('start_path is '+start_path)
	
	arc_files=full_file_list(sync_path+'/'+SYNC_SUBDIR)
	for idx in range(0,len(arc_files)):
		arc_files[idx]=arc_files[idx][len(sync_path)+len('/'):]
		src=arc_files[idx]
		dest=start_path+arc_files[idx][len(SYNC_SUBDIR):]
#		print('got archived file at path     ./'+src)
#		print('possible destination          '+dest)
		
		#if the destination file does exist
		if(os.path.isfile(dest)):
			#check if there are differences using 'diff'
			command=['diff',src,dest]
			sub_proc=subprocess.Popen(' '.join(command),stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True)
			output,error=sub_proc.communicate()
			output=output.decode('utf-8')
			
			#if so, prompt the user to resolve the differences
			if(len(output)>0):
				print('found differences between '+src+' and '+dest+'!')
				
				#resolve conflicts in this case
				resolve_bk(src,dest)
			#else just skip it (no differences)
			else:
				print('no differences found; skipping '+dest+'...')
				continue
		#if the destination file doesn't already exist
		else:
			print('destination '+dest+' does not yet exist! (new or moved file?)')
			
			#TODO: handle moved files gracefully
			#look for a file with the same name
				#if a file with the same name is found
					#run diff
					#if there are no differences, prompt to move local file
					#if there are differences, prompt for directory and what to do
			#TODO: copy src to the appropriate destination
	
	#clean up backup dir
	os.chdir(run_dir)
	print('removing '+sync_path)
	os.system('rm -rf '+sync_path)

#TODO: write this, and provide a cli option to use it
#difference a two backup files by using tar tvf and diff
def diff_bk():
	pass

if(__name__=='__main__'):
	parser=optparse.OptionParser()
	
	parser.add_option('--extract',action='store_true',dest='extract',default=False)
	parser.add_option('--syncf',action='store',dest='sync_file',default=os.environ['HOME']+'/sync_bk_'+time.strftime('%Y-%m-%d')+'.tar.gz')
	parser.add_option('--syncd',action='store',dest='sync_dir',default=tempfile.gettempdir())
	parser.add_option('--manifest',action='store',dest='manifest',default=os.environ['HOME']+'/.config/sync_bk/sync_manifest.json')
	
	options=parser.parse_args(sys.argv[1:])
	
	extract=options[0].extract
	sync_file=options[0].sync_file
	sync_dir=options[0].sync_dir
	manifest=options[0].manifest
	
	if(extract):
		print('Synching backup (extracting) from file '+sync_file)
		sync_bk(sync_file,sync_dir)
	else:
		print('Creating a backup using manifest file '+str(manifest)+'; storing output in '+str(sync_file))
		mk_bk(manifest,sync_file,sync_dir)
	
	

