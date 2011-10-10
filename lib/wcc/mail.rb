
module WCC
	# An email address container with internal conversion
	# routines.
	class MailAddress
		def initialize(email)
			email = email.to_s if email.is_a?(MailAddress)
			@email = email.strip
		end
		
		# Extract the 'name' out of an mail address
		#   "Me <me@example.org>" -> "Me"
		#   "me2@example.org" -> "me2"
		#
		# @return [String] name
		def name
			if @email =~ /^[\w\s]+<.+@[^@]+>$/
				@email.gsub(/<.+?>/, '').strip
			else
				@email.split("@")[0...-1].join("@")
			end
		end

		# Return the real mail address
		#   "Me <me@example.org>" -> "me@example.org"
		#   "me2@example.org" -> "me2@example.org"
		#
		# @return [String] mail address
		def address
			if @email =~ /^[\w\s]+<.+@[^@]+>$/
				@email.match(/<([^>]+@[^@>]+)>/)[1]
			else
				@email
			end
		end
		
		def to_s; @email end
	end

	# SmtpMailer is a specific implementation of an mail deliverer that
	# does plain SMTP to host:port using [Net::SMTP].
	class SmtpMailer
		def initialize(host, port)
			@host = host
			@port = port
		end
		
		# Sends a mail built up from some [ERB] templates to the
		# specified adresses.
		#
		# @param [OpenStruct] data used to construct ERB binding
		# @param [ERB] main the main template
		# @param [Hash] bodies :name, ERB template pairs
		# @param [String] from the From: address
		# @param [Array] tos array of To: addresses
		def send(data, main, bodies, from, tos = [])
			# generate a boundary that may be used for multipart
			data.boundary = "frontier-#{data.site.id}"
			# generate messages
			msgs = {}
			tos.each do |to|
				data.bodies = {}
				# eval all body templates
				bodies.each do |name,template|
					data.bodies[name] = template.result(binding)
				end
				# eval main template
				msgs[to] = main.result(binding)
			end
			# send messages
			Net::SMTP.start(@host, @port) do |smtp|
				msgs.each do |to,msg|
					smtp.send_message(msg, from.address, to.address)
				end
			end
		rescue
			WCC.logger.fatal "Cannot send mails via SMTP to #{@host}:#{@port} : #{$!.to_s}"
		end
	end
end