# This file is part of CONCEPT, the cosmological N-body code in Python.
# Copyright (C) 2015 Jeppe Mosgard Dakin.
#
# CONCEPT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CONCEPT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CONCEPT. If not, see http://www.gnu.org/licenses/
#
# The auther of CONCEPT can be contacted at
# jeppe.mosgaard.dakin(at)post.au.dk
# The latest version of CONCEPT is available at
# https://github.com/jmd-dk/concept/



# Import everything from the commons module. In the .pyx file,
# this line will be replaced by the content of commons.py itself.
from commons import *

# Imports for 3D plotting
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import juggle_axes

# Seperate but equivalent imports in pure Python and Cython
if not cython.compiled:
    pass
else:
    # Lines in triple quotes will be executed in the .pyx file.
    """
    """

# Imports and definitions common to pure Python and Cython
import pexpect
import subprocess

@cython.header(# Arguments
               data_or_filename='object',
               # Locals
               filename='str',
               header='str',
               i='int',
               k='double[::1]',
               k_unit='double',
               k_unit_from_file='double',
               power='double[::1]',
               power_unit='double',
               power_unit_from_file='double',
               power_σ='double[::1]',
               power_σ_unit_from_file='double',
               tmp='str',
               )
def plot_powerspec(data_or_filename):
    # Only the master process takes part in the plotting
    if not master:
        return

    # If a filename is provided in stead of data, the data should be
    # read in from the file. In that case, the plot should be saved to
    # filename + '.png'. Otherwize, the argument should be a tuple
    # consisting of a filename to save to, k, power and power_σ.
    if isinstance(data_or_filename, str):
        filename = data_or_filename + '.png'
        masterprint('Plotting power spectrum and saving to "{}" ...'
                    .format(filename))
        # Read in data
        k, power, power_σ = loadtxt(filename, unpack=True, skiprows=2)
        # Read in meta data (units)
        with open(filename, encoding='utf-8') as powespec_file:
            for i in range(2):
                header = powespec_file.readline()
        k_unit_from_file = eval('units.' + re.search('k \[(.*?)\]', header).group(1).replace('⁻¹', '**(-1)'))
        power_unit_from_file = eval('units.' + re.search('power \[(.*?)\]', header).group(1).replace('³', '**3'))
        power_σ_unit_from_file = eval('units.' + re.search('σ\(power\) \[(.*?)\]', header).group(1).replace('³', '**3'))
        # Multiply by the units
        k = asarray(k)*k_unit_from_file
        power = asarray(power)*power_unit_from_file
        power_σ = asarray(power_σ)*power_σ_unit_from_file
        # Attach extension to filename regardless of current extension
        filename = filename + '.png'
    else:
        filename = data_or_filename[0]
        # Attach missing extension to filename
        if not filename.endswith('.png'):
            filename += '.png'
        masterprint('Plotting power spectrum and saving to "{}" ...'
                    .format(filename))
        # Unpack data
        _, k, power, power_σ = data_or_filename
    # Transform quantities to desired units
    k_unit = 1/units.Mpc
    power_unit = units.Mpc3
    k = asarray(k)/k_unit
    power = asarray(power)/power_unit
    power_σ = asarray(power_σ)/power_unit
    # Plot powerspectrum
    plt.figure()
    plt.gca().set_xscale('log')
    plt.gca().set_yscale('log', nonposy='clip')
    plt.errorbar(k, power, yerr=power_σ, fmt='b.', ms=3, ecolor='r', lw=0)
    plt.xlabel('$k\,\mathrm{[Mpc^{-1}]}$')
    plt.ylabel('$\mathrm{power}\,\mathrm{[Mpc^3]}$')
    tmp = '{:.1e}'.format(min(k))
    plt.xlim(xmin=float(tmp[0] + tmp[3:]))
    tmp = '{:.1e}'.format(max(k))
    plt.xlim(xmax=float(str(int(tmp[0]) + 1) + tmp[3:]))
    tmp = '{:.1e}'.format(min(power))
    plt.ylim(ymin=float(tmp[0] + tmp[3:]))
    tmp = '{:.1e}'.format(np.max(asarray(power) + asarray(power_σ)))
    plt.ylim(ymax=float(str(int(tmp[0]) + 1) + tmp[3:]))
    plt.savefig(filename)
    # Finish progress message
    masterprint('done')


# Setting up figure and plot the particles
@cython.header(# Arguments
               particles='Particles',
               a='double',
               filename='str',
               # Locals
               a_str='str',
               alpha='double',
               alpha_min='double',
               basename='str',
               combined='double[:, :, ::1]',
               dirname='str',
               N='Py_ssize_t',
               N_local='Py_ssize_t',
               renderpart_filename='str',
               renderpart_filenames='list',
               renderparts_dirname='str',
               i='int',
               r='int',
               size='double',
               size_max='double',
               size_min='double',
               )
def render(particles, a, filename):
    global artist_particles, artist_text, ax
    # Attach missing extension to filename
    if not filename.endswith('.png'):
        filename += '.png'
    # Print out progress message
    masterprint('Rendering and saving image "{}" ...'.format(filename))
    # Extract particle data
    N = particles.N
    N_local = particles.N_local
    # Update particle positions on the figure
    artist_particles._offsets3d = juggle_axes(particles.posx_mv[:N_local],
                                              particles.posy_mv[:N_local],
                                              particles.posz_mv[:N_local],
                                              zdir='z')
    # The particle size on the figure.
    # The size is chosen such that the particles stand side by side in a
    # homogeneous unvierse (more or less).
    size = 1000*np.prod(fig.get_size_inches())/N**ℝ[2/3]
    # The particle alpha on the figure.
    # The alpha is chosen such that in a homogeneous unvierse, a column
    # of particles have a collective alpha of 1 (more or less).
    alpha = N**ℝ[-1/3]
    # Alpha values lower than alpha_min appear completely invisible.
    # Allow no alpha values lower than alpha_min. Shrink the size to
    # make up for the large alpha.
    alpha_min = 0.0059
    if alpha < alpha_min:
        size *= alpha/alpha_min
        alpha = alpha_min
    # Apply size and alpha
    artist_particles.set_sizes([size])
    artist_particles.set_alpha(alpha)
    # Print the current scale factor on the figure
    if master:
        artist_text.set_text('')
        a_str = significant_figures(a, 4, just=0, scientific=True)
        artist_text = ax.text(+0.25*boxsize,
                              -0.3*boxsize,
                              0,
                              '$a = {}$'.format(a_str),
                              fontsize=16,
                              )
        # Make the text color black or white, dependent on the bgcolor
        if sum(bgcolor) < 1:
            artist_text.set_color('white')
        else:
            artist_text.set_color('black')
    # Update axis limits if a boxsize were explicitly passed
    if boxsize:
        ax.set_xlim(0, boxsize)
        ax.set_ylim(0, boxsize)
        ax.set_zlim(0, boxsize)
    # If running with a single process, save the render, make a call to
    # update the liverender and then return.
    if nprocs == 1:
        plt.savefig(filename, bbox_inches='tight', pad_inches=0)
        masterprint('done')
        update_liverender(filename)
        return
    # Running with multiple processes.
    # Each process save its rendered part to disk.
    # First, make a temporary directory to hold the render parts.
    dirname = os.path.dirname(filename)
    basename = os.path.basename(filename)
    renderparts_dirname = '{}/.renderparts'.format(dirname)
    renderpart_filename = '{}/rank{}.{}'.format(renderparts_dirname,
                                                rank,
                                                basename)
    if master:
        os.makedirs(renderparts_dirname, exist_ok=True)
    # Now save the render parts, including transparency
    Barrier()
    plt.savefig(renderpart_filename,
                bbox_inches='tight',
                pad_inches=0,
                transparent=True,
                )
    Barrier()
    # The master process combines the parts using ImageMagick
    if master:
        # List of all newly created renderparts
        renderpart_filenames = [(renderparts_dirname + '/rank{}.' + basename)
                                 .format(r) for r in range(nprocs)]
        # Combine all render parts into one,
        # with the correct background color and no transparency.
        subprocess.call([paths['convert']] + renderpart_filenames
                         + ['-background', 'rgb({}%, {}%, {}%)'
                                            .format(100*bgcolor[0],
                                                    100*bgcolor[1],
                                                    100*bgcolor[2]),
                            '-layers', 'flatten', '-alpha', 'remove',
                            filename])
        # Remove the temporary directory
        shutil.rmtree(renderparts_dirname)
    masterprint('done')
    # Update the live render (local and remote)
    update_liverender(filename)

# Update local and remote live renders
@cython.header(# Arguments
               filename='str',
               )
def update_liverender(filename):
    # Updating the live render cannot be done in parallel
    if not master:
        return
    # Update the live render with the newly produced render 
    if liverender:
        masterprint('Updating live render "{}" ...'.format(liverender),
                    indent=4)
        shutil.copy(filename, liverender)
        masterprint('done')
    # Updating the remote live render with the newly produced render
    if not remote_liverender or not scp_password:
        return
    cmd = 'scp "{}" "{}"'.format(filename, remote_liverender)
    scp_host = re.search('@(.*):', remote_liverender).group(1)
    scp_dist = re.search(':(.*)',  remote_liverender).group(1)
    masterprint('Updating remote live render "{}:{}" ...'.format(scp_host,
                                                                 scp_dist),
                indent=4)
    expects = ['password.',
               'passphrase.',
               'continue connecting',
               pexpect.EOF,
               pexpect.TIMEOUT,
               ]
    child = pexpect.spawn(cmd, timeout=15, env={'SSH_ASKPASS': '',
                                                'DISPLAY'    : ''})
    for i in range(2):
        n = child.expect(expects)
        if n < 2:
            # scp asks for password or passphrase. Supply it
            child.sendline(scp_password)
        elif n == 2:
            # scp cannot authenticate host. Connect anyway
            child.sendline('yes')
        elif n == 3:
            break
        else:
            child.kill(9)
            break
    child.close(force=True)
    if child.status:
        msg = "Remote live render could not be scp'ed to" + scp_host
        masterwarn(msg)
    else:
        masterprint('done')

# This function projects the particle positions onto the xy-plane
# and renders this projection directly in the terminal, using
# ANSI/VT100 control sequences.
@cython.header(# Arguments
               particles='Particles',
               # Locals
               N='Py_ssize_t',
               N_local='Py_ssize_t',
               colornumber='unsigned long long int',
               i='Py_ssize_t',
               j='Py_ssize_t',
               maxval='unsigned long long int',
               posx='double*',
               posy='double*',
               projection='unsigned long long int[:, ::1]',
               projection_ANSI='list',
               scalec='double',
               scalex='double',
               scaley='double',
               )
def terminal_render(particles):
    # Extract particle data
    N = particles.N
    N_local = particles.N_local
    posx = particles.posx
    posy = particles.posy
    # Project particle positions onto a 2D array,
    # counting the number of particles in each pixel.
    projection = np.zeros((terminal_resolution//2, terminal_resolution),
                          dtype=C2np['unsigned long long int'])
    scalex = projection.shape[1]/boxsize
    scaley = projection.shape[0]/boxsize
    for i in range(N_local):
        projection[cast(particles.posy[i]*scaley, 'Py_ssize_t'),
                   cast(particles.posx[i]*scalex, 'Py_ssize_t')] += 1
    Reduce(sendbuf=(MPI.IN_PLACE if master else projection),
           recvbuf=(projection   if master else None),
           op=MPI.SUM)
    if not master:
        return
    # Values in the projection array equal to or larger than maxval
    # will be mapped to color nr. 255. The numerical coefficient is
    # more or less arbitrarily chosen.
    maxval = 12*N//(projection.shape[0]*projection.shape[1])
    if maxval < 5:
        maxval = 5
    # Construct list of strings, each string being a space prepended
    # with an ANSI/VT100 control sequences which sets the background
    # color. When printed together, these strings produce an ANSI image
    # of the projection.
    projection_ANSI = []
    scalec = 240.0/maxval
    for i in range(projection.shape[0]):
        for j in range(projection.shape[1]):
            colornumber = cast(16 + projection[i, j]*scalec, 'unsigned long long int')
            if colornumber > 255:
                colornumber = 255
            if colornumber < 16 or colornumber > 255:
                masterprint('wrong color:', colornumber, projection[i, j], scalec, projection[i, j]*scalec, maxval)
                sleep(1000)
            projection_ANSI.append('\x1b[48;5;{}m '.format(colornumber))
        projection_ANSI .append('\x1b[0m\n')
    # Print the ANSI image
    masterprint(''.join(projection_ANSI), end='')

# This function formats a floating point
# number f to only have n significant figures.
@cython.header(# Arguments
               f='double',
               n='int',
               just='int',
               scientific='bint',
               # Locals
               e_index='int',
               f_str='str',
               power='int',
               power10='double',
               sign='int',
               returns='str',
               )
def significant_figures(f, n, just=0, scientific=False):
    sign = 1
    if f == 0:
        # Nothing fancy happens to zero
        return '0'.ljust(n + 1)
    elif f < 0:
        # Remove the minus sign, for now
        sign = -1
        f *= sign
    # Round to significant digits
    power = n - 1 - int(log10(f))
    power10 = 10.0**power
    f = round(f*power10)/power10
    f_str = str(f)
    # Convert to e notation if f is very large or very small
    if (len(f_str) - 1 - (f_str[(len(f_str) - 2):] == '.0') > n
        and not (len(f_str) > 2
                 and f_str[:2] == '0.'
                 and f_str[2] != '0')):
        f_str = ('{:.' + str(n) + 'e}').format(f)
    if 'e' in f_str:
        # In scientific (e) notation
        e_index = f_str.find('e')
        f_str = f_str[:np.min(((n + 1), e_index))] + f_str[e_index:]
        if scientific:
            e_index = f_str.find('e')
            f_str = (f_str.replace('e', r'\times 10^{'
                     + f_str[(e_index + 1):].replace('+', '') + '}'))
            f_str = f_str[:(f_str.find('}') + 1)]
        # Put sign back in
        if sign == -1:
            f_str = '-' + f_str
        return f_str.ljust(just)
    else:
        # Numbers which do not need *10^? to be nicely expressed
        if len(f_str) == n + 2 and (f_str[(len(f_str) - 2):] == '.0'):
            # Unwanted .0
            f_str = f_str[:n]
        elif (len(f_str) - 1 - (f_str[:2] == '0.')) < n:
            # Pad with zeros to get correct amount of figures
            f_str += '0'*(n - (len(f_str) - 1) + (f_str[:2] == '0.'))
        # Put sign back in
        if sign == -1:
            f_str = '-' + f_str
        return f_str.ljust(just)

# Set up figure.
# The 77.50 scaling is needed to map the resolution to pixel units
fig = plt.figure(figsize=[resolution/77.50]*2)
ax = fig.gca(projection='3d', axisbg=bgcolor)
ax.set_aspect('equal')
ax.dist = 8.55  # Zoom level
# The artist for the particles
artist_particles = ax.scatter(0, 0, 0, color=color, lw=0)
# The artist for the scalefactor text
artist_text = ax.text(0, 0, 0, '')
# Configure axis options
ax.set_xlim(0, boxsize)
ax.set_ylim(0, boxsize)
ax.set_zlim(0, boxsize)
ax.w_xaxis.set_pane_color(zeros(4))
ax.w_yaxis.set_pane_color(zeros(4))
ax.w_zaxis.set_pane_color(zeros(4))
ax.w_xaxis.gridlines.set_lw(0)
ax.w_yaxis.gridlines.set_lw(0)
ax.w_zaxis.gridlines.set_lw(0)
ax.grid(False)
ax.w_xaxis.line.set_visible(False)
ax.w_yaxis.line.set_visible(False)
ax.w_zaxis.line.set_visible(False)
ax.w_xaxis.pane.set_visible(False)
ax.w_yaxis.pane.set_visible(False)
ax.w_zaxis.pane.set_visible(False)
for tl in ax.w_xaxis.get_ticklines():
    tl.set_visible(False)
for tl in ax.w_yaxis.get_ticklines():
    tl.set_visible(False)
for tl in ax.w_zaxis.get_ticklines():
    tl.set_visible(False)
for tl in ax.w_xaxis.get_ticklabels():
    tl.set_visible(False)
for tl in ax.w_yaxis.get_ticklabels():
    tl.set_visible(False)
for tl in ax.w_zaxis.get_ticklabels():
    tl.set_visible(False)

# Construct instance of the colormap with 256 - 16 = 240 colors
colormap_240 = getattr(matplotlib.cm, terminal_colormap)(arange(240))[:, :3]
# Apply the colormap to the terminal, remapping the 240 higher color
# numbers. The 16 lowest are left alone in order not to mess with
# standard terminal coloring.
if terminal_render_times:
    for i in range(240):
        colorhex = matplotlib.colors.rgb2hex(colormap_240[i])
        masterprint('\x1b]4;{};rgb:{}/{}/{}\x1b\\'
                     .format(16 + i, colorhex[1:3],
                                     colorhex[3:5],
                                     colorhex[5:]), end='')
