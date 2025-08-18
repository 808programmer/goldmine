import requests
import time
import tempfile
import zipfile
import json
import os
from django.conf import settings
import logging
from decouple import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class AdobeOCRService:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        
        # Configure retry strategy for network requests
        self.session = requests.Session()
        retry_strategy = Retry(
            total=1,  # Reduced from 3 to 1 to avoid aggravating rate limits
            backoff_factor=5,  # Increased backoff to 5 seconds
            status_forcelist=[500, 502, 503, 504],  # Removed 429 from retry list
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def clear_cached_token(self):
        """Force clear any cached access token"""
        self.access_token = None
        self.token_expires_at = 0
        logger.info("Cleared cached Adobe access token")
    
    def refresh_credentials(self):
        """Force refresh credentials by clearing cache and getting new token"""
        self.clear_cached_token()
        return self._get_access_token()
    
    def _get_access_token(self):
        """Get access token using OAuth Client Credentials flow"""
        # Check if we have a valid token
        current_time = time.time()
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
        
        # Check if credentials are configured
        if not settings.ADOBE_CLIENT_ID or not settings.ADOBE_CLIENT_SECRET:
            raise Exception("Adobe credentials are not configured. Please check your .env file.")
        
        # Check if credentials are default/placeholder values
        if (settings.ADOBE_CLIENT_ID == 'your_adobe_client_id' or 
            settings.ADOBE_CLIENT_SECRET == 'your_adobe_client_secret'):
            raise Exception("Please update your Adobe credentials in the .env file with actual values.")
        
        auth_url = "https://ims-na1.adobelogin.com/ims/token/v3"
        
        payload = {
            'client_id': str(settings.ADOBE_CLIENT_ID),
            'client_secret': str(settings.ADOBE_CLIENT_SECRET),
            'grant_type': 'client_credentials',
            'scope': 'openid,AdobeID,session,additional_info,read_organizations,read_organizations_external,read_profiles,write_profiles'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            # Use session with retry logic and timeout
            response = self.session.post(auth_url, data=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Adobe token response status: {response.status_code}")
                logger.error(f"Adobe token response content: {response.text}")
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Set expiration time (subtract 60 seconds for safety)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = current_time + expires_in - 60
            
            logger.info("Successfully obtained Adobe access token")
            return self.access_token
            
        except requests.exceptions.Timeout:
            logger.error("Timeout getting Adobe access token")
            raise Exception("Network timeout while authenticating with Adobe. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error getting Adobe access token")
            raise Exception("Network connection error while authenticating with Adobe. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Adobe access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
                if e.response.status_code == 429:
                    raise Exception("Adobe API rate limit reached. Please wait a few minutes before trying again.")
            raise Exception(f"Failed to authenticate with Adobe: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_file_path, use_fallback=False):
        """Extract text from PDF using Adobe REST API or fallback method"""
        try:
            if use_fallback:
                logger.info("Using fallback OCR method for faster processing")
                return self._fallback_ocr_extraction(pdf_file_path)
            
            # Step 1: Get access token
            access_token = self._get_access_token()
            
            # Step 2: Upload the PDF file
            asset_id = self._upload_file(pdf_file_path, access_token)
            
            # Step 3: Create extraction job
            job_location = self._create_extraction_job(asset_id, access_token)
            
            # Step 4: Poll for completion and get results
            extracted_text = self._poll_and_get_results(job_location, access_token)
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Adobe PDF extraction failed: {str(e)}")
            logger.info("Attempting fallback OCR method...")
            try:
                return self._fallback_ocr_extraction(pdf_file_path)
            except Exception as fallback_e:
                logger.error(f"Fallback OCR also failed: {str(fallback_e)}")
                # Raise a specific exception for OCR failure
                raise Exception(f"OCR extraction failed - Adobe OCR: {str(e)}, Fallback OCR: {str(fallback_e)}. This may be due to document size, length, or format issues. Please try again later or upload a different document.")
    
    def _fallback_ocr_extraction(self, pdf_file_path):
        """Fallback OCR using PyPDF2 or similar for faster processing"""
        try:
            import PyPDF2
            logger.info("Using PyPDF2 for fallback text extraction")
            
            extracted_text = ""
            with open(pdf_file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Could not extract text from page {page_num + 1}: {e}")
                        continue
            
            # If no text extracted, provide a placeholder instead of failing
            if not extracted_text.strip():
                logger.warning("No text could be extracted with PyPDF2 - this might be an image-based PDF")
                extracted_text = f"""
[FALLBACK OCR RESULT]
This PDF appears to be image-based or contains no extractable text.
File: {os.path.basename(pdf_file_path)}
Pages: {len(pdf_reader.pages)}
Status: Text extraction not possible with current method

For image-based PDFs, Adobe OCR is recommended but requires network connectivity.
This placeholder text allows the processing workflow to continue.
                """.strip()
            
            logger.info(f"Fallback extraction completed: {len(extracted_text)} characters")
            return extracted_text
            
        except ImportError:
            logger.error("PyPDF2 not available for fallback OCR")
            # Return a placeholder instead of failing
            return f"""
[FALLBACK OCR UNAVAILABLE]
PyPDF2 is not installed. This PDF could not be processed.
File: {os.path.basename(pdf_file_path)}
Status: OCR library not available

Please install PyPDF2 or ensure Adobe OCR is working.
            """.strip()
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            # Return a placeholder instead of failing
            return f"""
[FALLBACK OCR ERROR]
An error occurred during text extraction: {str(e)}
File: {os.path.basename(pdf_file_path)}
Status: Extraction failed

This allows the processing workflow to continue with placeholder data.
            """.strip()
    
    def _upload_file(self, pdf_file_path, access_token):
        """Upload PDF file to Adobe and get asset ID using two-step process"""
        
        # Step 1: Get upload URI
        upload_uri = self._get_upload_uri(access_token)
        
        # Step 2: Upload file to the URI
        asset_id = self._upload_to_uri(pdf_file_path, upload_uri, access_token)
        
        return asset_id
    
    def _get_upload_uri(self, access_token):
        """Get upload URI from Adobe"""
        upload_url = "https://pdf-services.adobe.io/assets"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': settings.ADOBE_CLIENT_ID,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'mediaType': 'application/pdf'
        }
        
        try:
            # Use session with retry logic and timeout
            response = self.session.post(upload_url, headers=headers, json=payload, timeout=30)
            
            logger.info(f"Get upload URI response status: {response.status_code}")
            logger.info(f"Get upload URI response: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            upload_uri = result.get('uploadUri')
            asset_id = result.get('assetID')
            
            if not upload_uri or not asset_id:
                logger.error(f"Missing upload URI or asset ID in response: {result}")
                raise Exception("No upload URI or asset ID returned")
            
            logger.info(f"Got upload URI and asset ID: {asset_id}")
            return {'upload_uri': upload_uri, 'asset_id': asset_id}
            
        except requests.exceptions.Timeout:
            logger.error("Timeout getting upload URI")
            raise Exception("Network timeout while getting upload URI. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error getting upload URI")
            raise Exception("Network connection error while getting upload URI. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get upload URI: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Upload URI response: {e.response.text}")
                if e.response.status_code == 429:
                    raise Exception("Adobe API rate limit reached while getting upload URI. Please wait 5-10 minutes before trying again.")
            raise Exception(f"Failed to get upload URI: {str(e)}")
    
    def _upload_to_uri(self, pdf_file_path, upload_info, access_token):
        """Upload file to the provided URI"""
        upload_uri = upload_info['upload_uri']
        asset_id = upload_info['asset_id']
        
        # Get file info
        file_name = os.path.basename(pdf_file_path)
        file_size = os.path.getsize(pdf_file_path)
        
        headers = {
            'Content-Type': 'application/pdf'
        }
        
        try:
            with open(pdf_file_path, 'rb') as file:
                # Debug: log file info and first bytes
                logger.info(f"Uploading file: {pdf_file_path}, size: {file_size}, name: {file_name}")
                first_bytes = file.read(8)
                logger.info(f"First 8 bytes: {first_bytes}")
                file.seek(0)
                
                file_data = file.read()
                
                # Use session with retry logic and longer timeout for file upload
                response = self.session.put(upload_uri, headers=headers, data=file_data, timeout=120)
                
                logger.info(f"File upload response status: {response.status_code}")
                
                response.raise_for_status()
                
                logger.info(f"Successfully uploaded PDF to URI, asset ID: {asset_id}")
                return asset_id
                
        except requests.exceptions.Timeout:
            logger.error("Timeout uploading file to URI")
            raise Exception("Network timeout while uploading file. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error uploading file to URI")
            raise Exception("Network connection error while uploading file. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"File upload to URI failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Upload to URI response status: {e.response.status_code}")
                logger.error(f"Upload to URI response: {e.response.text}")
            raise Exception(f"Failed to upload PDF file to URI: {str(e)}")
    
    def _create_extraction_job(self, asset_id, access_token):
        """Create text extraction job"""
        extract_url = "https://pdf-services.adobe.io/operation/extractpdf"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': settings.ADOBE_CLIENT_ID,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'assetID': asset_id,
            'elementsToExtract': ['text'],
            'renditionsToExtract': ['tables', 'figures']
        }
        
        try:
            logger.info(f"Creating extraction job for asset: {asset_id}")
            logger.info(f"Job creation URL: {extract_url}")
            logger.info(f"Job creation payload: {payload}")
            
            # Use session with retry logic and timeout
            response = self.session.post(extract_url, headers=headers, json=payload, timeout=30)
            
            logger.info(f"Job creation response status: {response.status_code}")
            logger.info(f"Job creation response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Get job location from headers
            location = response.headers.get('location')
            if not location:
                raise Exception("No job location returned")
            
            logger.info(f"Created extraction job, location: {location}")
            return location  # Return full location URL instead of just job ID
            
        except requests.exceptions.Timeout:
            logger.error("Timeout creating extraction job")
            raise Exception("Network timeout while creating extraction job. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error creating extraction job")
            raise Exception("Network connection error while creating extraction job. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Job creation failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Job creation response status: {e.response.status_code}")
                logger.error(f"Job creation response: {e.response.text}")
            raise Exception(f"Failed to create extraction job: {str(e)}")
    
    def _poll_and_get_results(self, job_location, access_token):
        """Poll for job completion and get results"""
        status_url = job_location  # Use the full location URL from job creation
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': settings.ADOBE_CLIENT_ID
        }
        
        max_attempts = 120  # 20 minutes max with faster polling
        attempt = 0
        
        logger.info(f"Starting to poll job status at: {status_url}")
        logger.info("Adobe OCR processing started. This may take 2-10 minutes depending on file size.")
        
        while attempt < max_attempts:
            try:
                # Use session with retry logic and timeout
                response = self.session.get(status_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                status = result.get('status')
                
                # More informative logging
                if attempt % 5 == 0:  # Log every 5th attempt to reduce noise
                    logger.info(f"Job status: {status} (attempt {attempt + 1}/{max_attempts})")
                
                if status == 'done':
                    # Adobe returns the ZIP file download URI in 'resource.downloadUri'
                    download_uri = None
                    
                    if 'resource' in result and 'downloadUri' in result['resource']:
                        download_uri = result['resource']['downloadUri']
                        logger.info(f"Found resource download URI")
                    elif 'content' in result and 'downloadUri' in result['content']:
                        download_uri = result['content']['downloadUri']
                        logger.info(f"Found content download URI")
                    elif 'asset' in result and 'downloadUri' in result['asset']:
                        download_uri = result['asset']['downloadUri']
                        logger.info(f"Found asset download URI")
                    
                    if download_uri:
                        logger.info("Adobe OCR processing completed successfully!")
                        return self._download_and_parse_result(download_uri, access_token)
                    else:
                        logger.error(f"No download URI found in response: {result}")
                        raise Exception("No download URI in completed job")
                
                elif status == 'failed':
                    error_message = result.get('error', {}).get('message', 'Unknown error')
                    raise Exception(f"Adobe extraction job failed: {error_message}")
                
                elif status in ['in progress', 'submitted']:
                    # Faster polling: more aggressive at the start
                    if attempt < 10:
                        sleep_time = 2  # First 10 attempts: 2 seconds
                    elif attempt < 30:
                        sleep_time = 3  # Next 20 attempts: 3 seconds
                    elif attempt < 60:
                        sleep_time = 5  # Next 30 attempts: 5 seconds
                    else:
                        sleep_time = 8  # After that: 8 seconds
                    
                    time.sleep(sleep_time)
                    attempt += 1
                else:
                    raise Exception(f"Unknown job status: {status}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"Timeout polling job status (attempt {attempt + 1})")
                # Continue polling on timeout
                time.sleep(5)
                attempt += 1
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error polling job status (attempt {attempt + 1})")
                # Continue polling on connection error
                time.sleep(5)
                attempt += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Status polling failed: {e}")
                raise Exception(f"Failed to poll job status: {str(e)}")
        
        raise Exception("Job polling timed out after 20 minutes")
    
    def _download_and_parse_result(self, download_uri, access_token):
        """Download and parse the extraction results"""
        try:
            # For S3 signed URLs, don't include additional auth headers
            # The URL already contains the authentication in the query parameters
            logger.info(f"Downloading result file...")
            
            # Use session with retry logic and longer timeout for download
            response = self.session.get(download_uri, timeout=120, stream=True)
            
            logger.info(f"Download response status: {response.status_code}")
            response.raise_for_status()
            
            # Stream download for better performance with large files
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Downloading {total_size} bytes...")
            
            # Save to temporary file with streaming
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and downloaded % 32768 == 0:  # Log every 32KB
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}%")
                
                temp_file_path = temp_file.name
            
            logger.info(f"Download complete, parsing content...")
            
            # Extract and parse JSON content
            extracted_text = self._parse_extraction_result(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
            logger.info(f"Text extraction complete, {len(extracted_text)} characters extracted")
            return extracted_text
            
        except requests.exceptions.Timeout:
            logger.error("Timeout downloading result file")
            raise Exception("Network timeout while downloading result file. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error downloading result file")
            raise Exception("Network connection error while downloading result file. Please check your internet connection.")
        except Exception as e:
            logger.error(f"Result download/parsing failed: {e}")
            raise Exception(f"Failed to download and parse results: {str(e)}")
    
    def _parse_extraction_result(self, zip_file_path):
        """Parse the extracted content from Adobe's response"""
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Look for the JSON file containing extracted content
                json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                
                if not json_files:
                    raise Exception("No JSON file found in extraction result")
                
                logger.info(f"Found {len(json_files)} JSON files, parsing largest one...")
                
                # Use the largest JSON file (likely contains the most content)
                json_file_sizes = [(f, zip_ref.getinfo(f).file_size) for f in json_files]
                largest_json_file = max(json_file_sizes, key=lambda x: x[1])[0]
                
                logger.info(f"Parsing {largest_json_file} ({zip_ref.getinfo(largest_json_file).file_size} bytes)")
                
                # Read and parse the JSON content efficiently
                with zip_ref.open(largest_json_file) as json_file:
                    content = json.load(json_file)
                
                # Extract text elements efficiently
                text_parts = []
                
                if 'elements' in content:
                    logger.info(f"Processing {len(content['elements'])} elements...")
                    for i, element in enumerate(content['elements']):
                        if i % 1000 == 0 and i > 0:  # Log progress for large documents
                            logger.info(f"Processed {i} elements...")
                        
                        if element.get('Text'):
                            text_parts.append(element['Text'])
                        elif element.get('text'):  # Alternative text field
                            text_parts.append(element['text'])
                
                extracted_text = "\n".join(text_parts) if text_parts else ""
                
                if not extracted_text.strip():
                    # Try alternative parsing
                    logger.info("Trying alternative text extraction...")
                    extracted_text = self._alternative_text_extraction(content)
                
                return extracted_text.strip()
                
        except Exception as e:
            logger.error(f"Failed to parse extraction result: {e}")
            raise Exception(f"Failed to parse extraction result: {str(e)}")
    
    def _alternative_text_extraction(self, content):
        """Alternative text extraction method"""
        try:
            text_parts = []
            
            # Try different content structures
            if 'document' in content:
                doc = content['document']
                if 'pages' in doc:
                    for page in doc['pages']:
                        if 'elements' in page:
                            for element in page['elements']:
                                if element.get('Text'):
                                    text_parts.append(element['Text'])
                                elif element.get('text'):
                                    text_parts.append(element['text'])
            
            # Try direct text extraction
            if 'text' in content:
                text_parts.append(content['text'])
            
            # Try content array
            if 'content' in content and isinstance(content['content'], list):
                for item in content['content']:
                    if isinstance(item, dict) and item.get('Text'):
                        text_parts.append(item['Text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
            
            return "\n".join(text_parts) if text_parts else ""
            
        except Exception as e:
            logger.error(f"Alternative text extraction failed: {e}")
            return ""
