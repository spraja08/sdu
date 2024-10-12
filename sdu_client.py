import argparse
import csv
import io
from Crypto.Cipher import AES
from Crypto.Util import Counter
import boto3
import base64
import json
import os

cim_fields = json.loads("""{
        "msisdn": {
            "type": "str",
            "pii": true
        },
        "email_id": {
            "type": "email",
            "pii": true
        },
        "call_time": {
            "type": "datetime"
        },
        "call_charge": {
            "type": "float"
        },
        "called_party": {
            "type": "str",
            "pii": true
        }
}""")

data_sources_mapping = json.loads("""{
    "voice" : {
        "type": "file",
        "format": "csv",
        "in_location": "data/incoming",
        "mapping": {
            "msisdn": 0,
            "email_id": 1,
            "call_time": 2,
            "call_charge": 3,
            "called_party": 4
        }
    }
}""")

class sdu_client():
    def __init__(self):
        secrets_manager = boto3.client("secretsmanager")
        response = secrets_manager.get_secret_value(SecretId='data-key')
        secret_value = response['SecretString']
        key = secret_value[:16].encode('utf-8')
        # ECB mode does not require an IV
        self.encrypt_cipher = AES.new(key, AES.MODE_ECB)
        self.decrypt_cipher = AES.new(key, AES.MODE_ECB)

    def encrypt(self, plaintext):
        # Pad plaintext to be a multiple of block size
        padded_plaintext = self._pad(plaintext.encode('utf-8'))
        ciphertext = self.encrypt_cipher.encrypt(padded_plaintext)
        return base64.b64encode(ciphertext).decode('utf-8')
        
    def decrypt(self, ciphertext):
        decoded_ciphertext = base64.b64decode(ciphertext)
        decrypted_padded = self.decrypt_cipher.decrypt(decoded_ciphertext)
        return self._unpad(decrypted_padded).decode('utf-8')

    def _pad(self, data):
        # Pad data to be a multiple of 16 bytes (AES block size)
        pad_length = 16 - (len(data) % 16)
        return data + bytes([pad_length] * pad_length)

    def _unpad(self, data):
        # Remove padding
        pad_length = data[-1]
        return data[:-pad_length]
    

    def encrypt_and_upload_file(self, data_source_type, input_dir, input_file_name, 
                                output_dir, output_file_name):
        s3_client = boto3.client('s3')
        cim_mapping = data_sources_mapping[data_source_type]["mapping"]
        output = io.StringIO()
        writer = csv.writer(output)

        with open(os.path.join(input_dir, input_file_name), 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                record = []
                for field in cim_mapping:
                    if "pii" in cim_fields[field] and cim_fields[field]["pii"]:
                        record.append(self.encrypt(row[cim_mapping[field]]))
                    else:
                        record.append(row[cim_mapping[field]])
                writer.writerow(record)
        output.seek(0)
        s3_client.put_object(Bucket=output_dir, Key=output_file_name, Body=output.getvalue())
        
    def decrypt_file(self, data_source_type, input_dir, input_file_name, 
                    output_dir, output_file_name):
        s3_client = boto3.client('s3')
        cim_mapping = data_sources_mapping[data_source_type]["mapping"]
        output = io.StringIO()
        writer = csv.writer(output)

        s3_object = s3_client.get_object(Bucket=input_dir, Key=input_file_name)
        s3_data = s3_object['Body'].read().decode('utf-8')
        reader = csv.reader(io.StringIO(s3_data))
        
        for row in reader:
            record = []
            for field in cim_mapping:
                if "pii" in cim_fields[field] and cim_fields[field]["pii"]:
                    record.append(self.decrypt(row[cim_mapping[field]]))
                else:
                    record.append(row[cim_mapping[field]])
            writer.writerow(record)
        output.seek(0)
        
        with open(os.path.join(output_dir, output_file_name), 'w') as file:
            file.write(output.getvalue())

def main(mode, data_source_type, input_dir, input_file_name, output_dir, output_file_name):
    client = sdu_client()
    if mode == 'test':
        plain_text = 'hey sinckers, come to appa'
        cipher_text = client.encrypt(plain_text)
        print(f"Encrypted: {cipher_text}")
        
        decrypted = client.decrypt(cipher_text)
        print(f"Decrypted: {decrypted}")
    else:
        if mode == "encrypt":
            client.encrypt_and_upload_file(data_source_type, input_dir, 
                                           input_file_name, output_dir, output_file_name)
            print(f"Encrypted {input_file_name} and uploaded to s3 bucket: {output_dir}")
        elif mode == "decrypt":
            client.decrypt_file(data_source_type, input_dir, 
                                           input_file_name, output_dir, output_file_name)
            print(f"Decrypted {input_file_name} and saved to: {output_dir}")

              
if __name__ == "__main__":
    #main("test")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="test | encrypt | decrypt")
    parser.add_argument("--data_source_type", help="voice | sms | data", default=None)
    parser.add_argument("--input_dir", help="Directory for incoming files", default=None)
    parser.add_argument("--output_dir", help="Directory for the output files", default=None)
    parser.add_argument("--input_file_name", help="incoming file name", default=None)
    parser.add_argument("--output_file_name", help="output file name", default=None)
    
    args = parser.parse_args()
    
    main(args.mode, args.data_source_type, args.input_dir, args.input_file_name,
         args.output_dir, args.output_file_name)  