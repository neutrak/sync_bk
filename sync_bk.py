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
import datetime

#the manifest file is json
import json

#command-line arguments are handled with an option parser
import optparse

#the manifest name (within the backup archive)
MANIFEST_NAME='sync_manifest.json'
SYNC_SUBDIR='sync_bk'

def unix_ts_to_str(ts):
	return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def cp_file(from_path,to_path,preserve_time=True):
	if(preserve_time):
		from_path=from_path.replace('\'','\\\'')
		from_path=from_path.replace(' ','\\ ')
		to_path=to_path.replace('\'','\\\'')
		to_path=to_path.replace(' ','\\ ')
		os.system('cp -v -p '+from_path+' '+to_path)
	else:
		shutil.copyfile(from_path,to_path)

def sync_cp_file(f,from_path,to_path):
	if((f['type']=='dir') or (f['type']=='directory')):
		if(f['recurse']==True):
			#copy all files in the directory, etc.
			shutil.copytree(os.path.join(from_path,f['path']),os.path.join(to_path,f['path']))
		else:
			os.makedirs(os.path.join(to_path,f['path']))
			for filename in os.listdir(os.path.join(from_path,f['path'])):
				if(not os.path.isdir(os.path.join(from_path,f['path'],filename))):
					cp_file(os.path.join(from_path,f['path'],filename),os.path.join(to_path,f['path'],filename))
	elif(f['type']=='file'):
		dir_ancestry=(f['path'].split(os.sep))
		directory=os.sep.join(dir_ancestry[0:len(dir_ancestry)-1])
		if(not os.path.exists(os.path.join(to_path,directory))):
			os.makedirs(os.path.join(to_path,directory))
		
		cp_file(os.path.join(from_path,f['path']),os.path.join(to_path,f['path']))
	else:
		print('Warn: Unrecognized file type for '+str(f)+'; skipping...')

def sync_add_file(f,output_arc):
	if(not os.path.exists(f['path'])):
		print('Warn: Nothing at path \''+f['path']+'\'; IGNORING!!!')
		return
	
	path=f['path'].replace('\'','\\\'')
	if((f['type']=='dir') or (f['type']=='directory')):
		if(f['recurse']==True):
			#copy all files in the directory, etc.
			cmd='tar uf '+output_arc+' --transform \'s%^%sync_bk/%\' \''+path+'\''
#			print('[debug] '+cmd)
			os.system(cmd)
		else:
			for filename in os.listdir(f['path']):
				if(not os.path.isdir(os.path.join(f['path'],filename))):
					cmd='tar uf '+output_arc+' --transform \'s%^%sync_bk/%\' \''+os.path.join(path,filename.replace('\'','\\\''))+'\''
#					print('[debug] '+cmd)
					os.system(cmd)
	elif(f['type']=='file'):
		cmd='tar uf '+output_arc+' --transform \'s%^%sync_bk/%\' \''+path+'\''
#		print('[debug] '+cmd)
		os.system(cmd)
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
	if(not manifest.startswith(os.sep)):
		manifest=os.path.join(run_dir,manifest)
	if(not output_file.startswith(os.sep)):
		output_file=os.path.join(run_dir,output_file)
	
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
		print('[debug] json_tree['+str(key)+']='+str(json_tree[key]))
	
	start_path=json_tree['start_path']
	if(start_path is None):
		start_path=os_environ['HOME']
	
	sync_path=os.path.join(sync_dir,SYNC_SUBDIR)
	try:
		os.mkdir(sync_path)
	except FileExistsError:
		print('Warn: '+sync_path+' already existed; if this script was previously run without a clean exit you should delete this first')
		print('Delete? (y/n)')
		option=(input().lower())[0]
		print('Got option '+str(option))
		
		if(option=='y'):
			print('[info] removing and re-making '+sync_path+'...')
			os.system('rm -rf '+sync_path)
			os.mkdir(sync_path)
	
	output_tar=output_file
	if(output_tar.endswith('.gz')):
		output_tar=output_tar[0:len(output_tar)-len('.gz')]
	
	os.chdir(start_path)
	for f in json_tree['files']:
		sync_add_file(f,output_tar)
	
	os.chdir(os.path.join(sync_path,'..'))
	
#	manifest_basename=os.path.basename(manifest)
	
	#enforce naming convention for manifest post-copy
	#because we need to know what to look for when extracting
	manifest_basename=MANIFEST_NAME
	
	shutil.copyfile(manifest,os.path.join(sync_path,'..',manifest_basename))
	
	cmd='tar uf '+output_tar+' --transform \'s%^%%\' '+manifest_basename
	print('[debug] '+cmd)
	os.system(cmd)
	
	cmd='gzip '+output_tar
	print('[debug] '+cmd)
	os.system(cmd)
	
	print('removing '+os.path.join(os.getcwd(),SYNC_SUBDIR+'')+' '+manifest_basename)
	os.system('rm -rf '+os.path.join(SYNC_SUBDIR,'')+' '+manifest_basename)

def resolve_bk(src,dest):
	got_opt=False
	
	src_info=os.stat(src)
	dest_info=os.stat(dest)
	
	while(not got_opt):
		print('Changes were found to the following file: '+dest)
		print('archive copy last modified time is '+unix_ts_to_str(src_info.st_mtime))
		print('filesystem copy last modified time is '+unix_ts_to_str(dest_info.st_mtime))
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
		print("\t"+'s[k]ip')
		print("?")
		
		option=(input().lower())[0]
		print('Got option '+str(option))
		
		#do what the option asked
		if(option=='n'):
			#keep newest
			print('[info] keeping newest')
			if(src_info.st_mtime>dest_info.st_mtime):
				cp_file(src,dest)
			got_opt=True
		elif(option=='o'):
			#keep oldest
			print('[info] keeping oldest')
			if(src_info.st_mtime<dest_info.st_mtime):
				cp_file(src,dest)
			got_opt=True
		elif(option=='l'):
			#keep largest
			print('[info] keeping largest')
			if(src_info.st_size>dest_info.st_size):
				#copy from source (archive) to destination
				cp_file(src,dest)
			got_opt=True
		elif(option=='s'):
			#keep smallest
			print('[info] keeping smallest')
			if(src_info.st_size<dest_info.st_size):
				#copy from source (archive) to destination
				cp_file(src,dest)
			got_opt=True
		elif(option=='a'):
			#keep archived copy (copy source to dest)
			print('[info] keeping archived copy')
			cp_file(src,dest)
			got_opt=True
		elif(option=='f'):
			#keep filesystem copy (do nothing)
			print('[info] keeping filesystem copy')
			got_opt=True
		elif(option=='d'):
			#view diff
			os.system('diff \''+src+'\' \''+dest+'\' | less')
		elif(option=='m'):
			#merge
			#TODO
			print('[info] merge not yet supported; skipping...')
			got_opt=True
		elif(option=='k'):
			#skip
			print('[info] skipping file')
			got_opt=True
		else:
			print('Warn: Unrecognized option, try again')
	
	#issue should now be resolved

#get all files (recursive os.listdir)
def full_file_list(start_path):
#	print('full_file_list debug; start_path='+start_path)
	
	acc=[]
	for f in os.listdir(start_path):
		fpath=os.path.join(start_path,f)
		if(os.path.isdir(fpath)):
			acc.extend(full_file_list(fpath))
		else:
			acc.append(fpath)
	return acc

#synchronize from a backup
def sync_bk(sync_file,sync_dir):
	#save the directory this script was run from
	run_dir=os.getcwd()
	
	sync_path=os.path.join(sync_dir,SYNC_SUBDIR)
	if(not os.path.exists(sync_path)):
		os.mkdir(sync_path)
	else:
		print('Warn: '+sync_path+' already existed; if this script was previously run without a clean exit you should delete this first')
		print('Delete? (y/n)')
		option=(input().lower())[0]
		print('Got option '+str(option))
		
		if(option=='y'):
			print('[info] removing and re-making '+sync_path+'...')
			os.system('rm -rf '+sync_path)
			os.mkdir(sync_path)
	
	print('[debug] '+os.getcwd()+'$ tar xzf -C \''+sync_path+'\' '+sync_file)
	os.system('tar -C \''+sync_path+'\' -xzf '+sync_file)
	
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
	
	print('[debug] start_path is '+start_path)
	
	arc_files=full_file_list(os.path.join(sync_path,SYNC_SUBDIR))
	for idx in range(0,len(arc_files)):
		arc_files[idx]=arc_files[idx][len(sync_path)+len(os.sep):]
		src=arc_files[idx]
		dest=start_path+arc_files[idx][len(SYNC_SUBDIR):]
		
		src=src.replace('\'','\\\'')
		dest=dest.replace('\'','\\\'')

#		print('[debug] got archived file at path     ./'+src)
#		print('[debug] possible destination          '+dest)
		
		#if the destination file does exist
		if(os.path.isfile(dest)):
			print('[debug] operating on file '+dest+' ...')
			if(not os.path.isfile(src)):
				print('[info] skipping '+dest+'; source was not a file')
				continue
			
			#compare checksums to determine if a file changed
			if(os.stat(src).st_size==os.stat(dest).st_size):
#				print('[debug] getting src checksum...')
				sub_proc=subprocess.Popen('sha1sum \''+src+'\' | awk \'{print $1}\'',stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True)
				src_sum,src_sum_error=sub_proc.communicate()
				src_sum=src_sum.decode('utf-8')
				
#				print('[debug] getting dest checksum...')
				sub_proc=subprocess.Popen('sha1sum \''+dest+'\' | awk \'{print $1}\'',stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True)
				dest_sum,dest_sum_error=sub_proc.communicate()
				dest_sum=dest_sum.decode('utf-8')
				
				#no differences; just skip it
				if(src_sum==dest_sum):
					print('[info] no differences found; skipping '+dest+'...')
					continue
			
			#there were differences,
			#so prompt the user to resolve the differences
			#they can view a diff if desired from resolv_bk
			print('[info] found differences between '+src+' and '+dest+' !')
			
			#resolve conflicts in this case
			resolve_bk(src,dest)
		#if the destination file doesn't already exist
		else:
			print('[info] destination '+dest+' does not yet exist! (new or moved file?)')
			
			#TODO: handle moved files gracefully
			#look for a file with the same name
				#if a file with the same name is found
					#run diff
					#if there are no differences, prompt to move local file
					#if there are differences, prompt for directory and what to do
			#copy src to the appropriate destination
			print('[info] copying '+src+' to '+dest)
			cp_file(src,dest)
	
	#clean up backup dir
	os.chdir(run_dir)
	print('[cleanup] removing '+sync_path)
	os.system('rm -rf '+sync_path)

#TODO: write this, and provide a cli option to use it
#difference a two backup files by using tar tvf and diff
def diff_bk():
	pass

if(__name__=='__main__'):
	parser=optparse.OptionParser()
	
	parser.add_option('--verbose',action='store_true',dest='verbose',default=False)
	parser.add_option('--extract',action='store_true',dest='extract',default=False)
	parser.add_option('--syncf',action='store',dest='sync_file',default=os.environ['HOME']+'/sync_bk_'+time.strftime('%Y-%m-%d')+'.tar.gz')
	parser.add_option('--syncd',action='store',dest='sync_dir',default=tempfile.gettempdir())
	parser.add_option('--manifest',action='store',dest='manifest',default=os.environ['HOME']+'/.config/sync_bk/sync_manifest.json')
	
	options=parser.parse_args(sys.argv[1:])
	
	verbose=options[0].verbose
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
	
	

