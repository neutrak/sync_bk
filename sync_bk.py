#!/usr/bin/env python3

#this backs up files (based on a manifest) into a .tar.gz file
#the .tar.gz can then be copied and un-packed to synchronize files

#we're gonna need some system calls for this
import sys
import os
import shutil

#general libraries
import tempfile
import time

#the manifest file is json
import json

#command-line arguments are handled with an option parser
import optparse

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
def mk_bk(manifest,output_file):
	#if the manifest file doesn't exist, then exit now!
	if(not os.path.isfile(manifest)):
		print('Err: Manifest file could not be opened (probably missing!), exiting...')
		exit(1)
	
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
	
	sync_path=tempfile.gettempdir()+'/sync_bk'
	os.mkdir(sync_path)
	
	for f in json_tree['files']:
		sync_cp_file(f,start_path,sync_path)
	
	os.chdir(sync_path+'/..')
	manifest_basename=os.path.basename(manifest)
	shutil.copyfile(manifest,sync_path+'/../'+manifest_basename)
	os.system('tar cvzf '+output_file+' '+manifest_basename+' sync_bk/')
	os.system('rm -rf sync_bk/ '+manifest_basename)

def resolv_bk(from_file,to_file):
	print('Changes were found to the following file: '+to_file)
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

#synchronize from a backup
def sync_bk(sync_file,sync_dir):
	#TODO: open sync_file, for each file in it,
	#	if the destination file doesn't already exist
	#		look for a file with the same name
	#			if a file with the same name is found
	#				run diff
	#				if there are no differences, prompt to move local file
	#				if there are differences, prompt for directory and what to do
	#		copy it to the appropriate destination
	#	if the destination file does exist
	#		check if there are differences using 'diff'
	#		if so, prompt the user to resolve the differences
	#		else just skip it (no differences)
	
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
		mk_bk(manifest,sync_file)
	
	

