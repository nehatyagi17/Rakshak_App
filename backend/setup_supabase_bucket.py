
import os
from supabase import create_client, Client
from decouple import config

url = config('SUPABASE_URL')
key = config('SUPABASE_KEY')

supabase: Client = create_client(url, key)

bucket_name = 'avatars'

try:
    # Try to get the bucket
    bucket = supabase.storage.get_bucket(bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except Exception as e:
    # Create the bucket if it doesn't exist
    print(f"Bucket '{bucket_name}' not found. Creating it...")
    try:
        supabase.storage.create_bucket(bucket_name, options={'public': True})
        print(f"Successfully created Public bucket: '{bucket_name}'")
    except Exception as create_error:
        print(f"Failed to create bucket: {create_error}")
        print("Please create a bucket named 'avatars' manually in your Supabase Dashboard (Storage -> New Bucket).")

print("Setup Complete.")
