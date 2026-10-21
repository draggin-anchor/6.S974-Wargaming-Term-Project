import sys; sys.path.insert(0,'.')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import wargame_gui as wg, snapshot as sn
g=wg.Graph('D1'); XY=sn.XY
fig,ax=plt.subplots(figsize=(5.2,4.6))
cols={'N':'#e3f2fd','C':'#fff3e0','S':'#fce4ec'}
names={'N':'North','C':'Center','S':'South'}
for r,nodes in wg.REGIONS.items():
    xs=[XY[v][0] for v in nodes]; ys=[XY[v][1] for v in nodes]
    ax.add_patch(plt.Rectangle((min(xs)-3,min(ys)-3),max(xs)-min(xs)+6,max(ys)-min(ys)+6,color=cols[r],zorder=0,lw=0))
    ax.text(min(xs)-2.7,max(ys)+2.0,names[r],fontsize=9,style='italic',color='#455a64')
for a,b in g.edges:
    d1 = 'PHL' in (a,b)
    ax.plot([XY[a][0],XY[b][0]],[XY[a][1],XY[b][1]],color='#1565c0' if d1 else '#90a4ae',ls='--' if d1 else '-',lw=1.2,zorder=1)
for v in g.nodes:
    x,y=XY[v]; k,o=wg.NODES[v][3],wg.NODES[v][4]
    if k=='home':
        ax.scatter([x],[y],marker='s',s=160,color=('#bbdefb' if v=='PHL' else '#1565c0') if o=='B' else '#c62828',edgecolor='k',lw=0.6,zorder=3)
    else:
        ax.scatter([x],[y],s=260,color='white',edgecolor='#37474f',lw=1.2,zorder=3)
    ax.text(x,y-1.9,wg.NODES[v][0],ha='center',va='top',fontsize=7.5)
ax.set_xlim(-6,37); ax.set_ylim(-8,30); ax.set_aspect('equal'); ax.axis('off')
fig.tight_layout(); fig.savefig('results/figures/network.png',dpi=220); fig.savefig('results/figures/network.pdf')
